"""Measure visible secondary motion relative to tracked anatomical carriers."""

import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import threading

import av
import cv2
import numpy as np
if __package__:
    from .media import presentation_offset
    from .progress import Progress
else:
    from media import presentation_offset
    from progress import Progress


def write_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(".partial")
    staged.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
    staged.replace(path)


def world_frame(fit):
    if not fit.pose_world_landmarks:
        return None
    return [[round(point.x, 5), round(point.y, 5), round(point.z, 5),
             round(min(point.visibility, point.presence), 3)]
            for point in fit.pose_world_landmarks[0]]


def world_track(fps, frames):
    return {"version": 1, "fps": fps, "frames": frames,
            "source": "MediaPipe Pose Landmarker monocular world estimates"}


def world_pose(source, model):
    """Estimate metric-space landmarks from the original monocular frames."""
    import mediapipe as mp

    vision = mp.tasks.vision
    config = vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=.3,
        min_tracking_confidence=.4,
    )
    with av.open(str(source)) as video, vision.PoseLandmarker.create_from_options(config) as detector:
        stream = video.streams.video[0]
        fps = float(stream.average_rate)
        stream.codec_context.thread_count = 3
        frames = []
        for frame in video.decode(stream):
            timestamp = int(frame.pts*frame.time_base*1000)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame.to_ndarray(format="rgb24"))
            frames.append(world_frame(detector.detect_for_video(image, timestamp)))
    return world_track(fps, frames)


class MatteFrames:
    """Read the exact foreground pages already registered to the source video."""

    def __init__(self, manifest, timeline_dir, size):
        self.manifest = manifest
        self.directory = timeline_dir
        self.size = size
        self.page = None
        self.atlas = None

    def read(self, index):
        grid = self.manifest["grid"]
        tile_width, tile_height = self.manifest["tile"]
        page, slot = divmod(index, grid*grid)
        if page != self.page:
            name = self.manifest["pages"][page][0]
            loaded = cv2.imread(str(self.directory/name), cv2.IMREAD_COLOR)
            self.atlas = loaded[...,2] if loaded is not None else None
            if self.atlas is None:
                raise ValueError(f"Missing matte atlas {name}")
            self.page = page
        column, row = slot%grid, slot//grid
        tile = self.atlas[row*tile_height:(row+1)*tile_height, column*tile_width:(column+1)*tile_width]
        return cv2.resize(tile, self.size, interpolation=cv2.INTER_LINEAR)


def joint_frames(manifest, regions):
    from cleanup_tracks import axial_anchors, lower_anchors, upper_anchors

    for values, frame in zip(manifest["frames"], regions):
        points = {key: (x/4, y/4, quality)
                  for key, (x, y, quality) in zip(manifest["landmarks"], values[1][0])}
        yield upper_anchors(points, frame)|lower_anchors(points, frame)|axial_anchors(points, frame)


def robust_region(previous, current, before, after, flow, quality, factor):
    """Remove each segment's observed 2D similarity before pooling surface flow."""
    height, width = quality.shape
    motion, trust = [], []
    for ellipse, destination, source, target in zip(previous, current, before, after):
        if any(value is None for value in (ellipse, destination, source, target)):
            continue
        start, end = np.asarray(source).reshape(2, 2)*factor
        start_next, end_next = np.asarray(target).reshape(2, 2)*factor
        vector, vector_next = end-start, end_next-start_next
        squared_length = vector@vector
        if squared_length < 9:
            continue
        cosine = float(vector@vector_next/squared_length)
        sine = float((vector[0]*vector_next[1]-vector[1]*vector_next[0])/squared_length)
        ratio = np.hypot(cosine, sine)
        if not .73<=ratio<=1.36 or cosine<.52 or np.linalg.norm(start_next-start)>42*factor:
            continue

        x, y, ux, uy, rx, ry = ellipse
        center = np.array([x, y])*factor
        radius = min(170, max(rx, ry))*factor
        left, right = max(0, int(center[0]-radius)), min(width, int(center[0]+radius+1))
        top, bottom = max(0, int(center[1]-radius)), min(height, int(center[1]+radius+1))
        if right<=left or bottom<=top:
            continue
        # Subsample large patches for equalized segment support.
        step = max(1, int(radius/16))
        ys, xs = np.mgrid[top:bottom:step,left:right:step]
        shifted_x, shifted_y = xs-center[0], ys-center[1]
        along = (shifted_x*ux+shifted_y*uy)/max(1,rx*factor)
        across = (shifted_y*ux-shifted_x*uy)/max(1,ry*factor)
        radial = along**2+across**2
        weights = quality[ys,xs]*np.maximum(0, 1-radial/.77)
        selected = weights>.05
        if np.count_nonzero(selected)<5:
            continue
        pixels = np.column_stack((xs[selected], ys[selected]))
        relative = pixels-start
        rotate = np.array([[cosine, sine],[-sine, cosine]])
        planned = start_next+relative@rotate-pixels
        residual = (flow[ys[selected],xs[selected]]-planned)/factor

        # An incorrect correspondence can have high texture. Use a
        # preliminary median and downweight inconsistent local velocities.
        weights = weights[selected]
        median = np.median(residual, axis=0)
        distance = np.linalg.norm(residual-median, axis=1)
        spread = float(np.median(distance))
        if np.linalg.norm(median)>25 or spread>13:
            continue
        weights *= np.exp(-.5*(distance/max(1.3,spread*1.6))**2)
        motion.append(np.average(residual, axis=0, weights=weights))
        motion.append((start_next+(center-start)@rotate-center)/factor)
        coverage = min(1., np.count_nonzero(selected)/max(6.,np.count_nonzero(radial<.77)*.35))
        trust.append(float(np.mean(weights)*coverage*np.exp(-spread/9)))
    if not trust or max(trust)<.075:
        return None
    combined = np.average(np.array(motion).reshape(-1,2,2), axis=0, weights=trust)
    return combined[0], combined[1], min(1.,max(trust)/.47)


def flow_workers():
    # Frame pairs are independent, so a few single-pair workers keep the cores busy
    # while the other preparation workers run.
    return max(1, min(4, (os.cpu_count() or 2) // 3))


def analyze_flow(source, manifest, timeline_dir, regions, factor):
    cv2.setNumThreads(2)
    source_width, source_height = manifest["frames"][0][0], manifest["height"]
    width,height = round(source_width*factor),round(source_height*factor)
    if min(width,height)<16:
        raise ValueError("Flow resolution too small")
    # Integer flow dimensions can round differently on each axis. Use their mean scale for local distances.
    factor=(width/source_width+height/source_height)/2
    matte_frames = MatteFrames(manifest, timeline_dir, (width,height))
    anchors = list(joint_frames(manifest, regions))
    yy,xx = np.mgrid[:height,:width].astype("float32")
    local = threading.local()

    def estimators():
        # DIS objects keep internal buffers, so every worker thread owns its own pair.
        if not hasattr(local, "pair"):
            pair = []
            for _ in range(2):
                estimator = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_FAST)
                estimator.setFinestScale(0)
                pair.append(estimator)
            local.pair = pair
        return local.pair

    def measure(index, prev_gray, gray, prev_matte, matte):
        forward, backward = estimators()
        values = {}
        flow = forward.calc(prev_gray,gray,None)
        reverse = backward.calc(gray,prev_gray,None)
        map_x, map_y = xx+flow[...,0], yy+flow[...,1]
        returned = cv2.remap(reverse,map_x,map_y,cv2.INTER_LINEAR)
        err = np.linalg.norm(flow+returned,axis=2)
        foreground = np.minimum(prev_matte,cv2.remap(matte,map_x,map_y,cv2.INTER_LINEAR))
        dx = cv2.Sobel(prev_gray,cv2.CV_32F,1,0,ksize=3)
        dy = cv2.Sobel(prev_gray,cv2.CV_32F,0,1,ksize=3)
        texture = np.clip((np.hypot(dx,dy)-4)/42,0,1)
        confidence = texture*np.exp(-.5*(err/1.2)**2)*np.clip((foreground.astype(float)-135)/92,0,1)
        confidence[(map_x<0)|(map_y<0)|(map_x>=width-1)|(map_y>=height-1)] = 0
        old, new = regions[index-1],regions[index]
        for key in old.keys()&new.keys()&anchors[index-1].keys()&anchors[index].keys():
            result = robust_region(old[key],new[key],anchors[index-1][key],anchors[index][key],
                                   flow,confidence,factor)
            if result is not None:
                values[key]=result
        return values

    shots = {start for start,_ in manifest["shots"]}
    measured = []
    pending = deque()
    workers = flow_workers()
    progress = Progress(len(regions))

    def collect(limit):
        while len(pending) > limit:
            item = pending.popleft()
            measured.append(item.result() if hasattr(item, "result") else item)
            progress.update(len(measured))

    prev_gray = prev_matte = None
    with av.open(str(source)) as video, ThreadPoolExecutor(workers) as pool:
        stream = video.streams.video[0]
        stream.codec_context.thread_count=3
        if (stream.width,stream.height)!=(source_width,source_height):
            raise ValueError("Optical flow must analyze the region track's source resolution")
        for index,frame in enumerate(video.decode(stream)):
            if abs(float(frame.pts*frame.time_base)-manifest.get("presentationStart",0)-
                   presentation_offset(manifest,index))>.002:
                raise ValueError("Motion and source timestamps do not match")
            gray = cv2.resize(frame.to_ndarray(format="gray"), (width,height), interpolation=cv2.INTER_AREA)
            matte = matte_frames.read(index)
            if index not in shots and prev_gray is not None:
                pending.append(pool.submit(measure, index, prev_gray, gray, prev_matte, matte))
            else:
                pending.append({})
            # Results are collected in frame order with a bounded number in flight.
            collect(workers * 3)
            prev_gray,prev_matte=gray,matte
            if index%120==0:
                print(f"Measured motion frame {index}",flush=True)
        collect(0)
    progress.finish()
    if len(measured)!=len(regions):
        raise ValueError("Decoded frame count and regions differ")
    return measured


def displacement_series(measured, fps):
    """Create bounded, causal projected displacement tracks plus carrier drive."""
    series, drive_frames = [], []
    offsets, centers, velocities = {}, {}, {}
    memory, drift = np.exp(-1/(fps*.25)),np.exp(-1/(fps*.44))
    for frame in measured:
        tracks, drives = {}, {}
        for key,(velocity, carrier, q) in sorted(frame.items()):
            if q<.16:
                continue
            offset = memory*offsets.get(key,np.zeros(2))+velocity*q
            center = drift*centers.get(key,np.zeros(2))+(1-drift)*offset
            offsets[key], centers[key] = offset, center
            delta = np.clip(offset-center,-18,18)
            tracks[key] = [float(delta[0]),float(delta[1]),float(q)]
            if key in velocities:
                acc = np.clip(carrier-velocities[key],-20,20)
                drives[key] = [float(acc[0]),float(acc[1])]
        offsets = {key:offsets[key] for key in tracks}
        centers = {key:centers[key] for key in tracks}
        velocities = {key:frame[key][1] for key in tracks}
        series.append(tracks)
        drive_frames.append(drives)
    return series, drive_frames


def response(drives, present, a1, a2):
    # Reset on the same observation gaps in both candidate and rigid baseline.
    output = np.zeros_like(drives)
    for i in range(2,len(drives)):
        if present[i] and present[i-1] and present[i-2]:
            output[i] = a1*output[i-1]+a2*output[i-2]+drives[i]
    return output


def lag_diagnostic(target, drive, visible, split, fps):
    """Measure antiphase residual/acceleration correlation on training only."""
    strongest = None
    for lag in range(round(fps*.25)+1):
        end = np.arange(lag,split)
        start = end-lag
        good = visible[end]&visible[start]
        if np.count_nonzero(good)<18:
            continue
        observed = target[end[good]]
        forcing = -drive[start[good]]
        observed -= observed.mean(axis=0)
        forcing -= forcing.mean(axis=0)
        scale = np.linalg.norm(observed)*np.linalg.norm(forcing)
        if scale>1e-8:
            score = float(np.sum(observed*forcing)/scale)
            if strongest is None or score>strongest[0]:
                strongest = (score,lag)
    if strongest is None or strongest[0]<.10:
        return {"frames":None,"correlation":None}
    return {"frames":strongest[1],"correlation":round(strongest[0],4)}


def observed_sequence_scores(target, drive, quality, train, holdout):
    """Fit one-step dynamics of the recorded residual sequence.

    Prior observed residuals are valid only for recorded playback. This score
    is deliberately separate from the free-running user-motion evaluation.
    """
    def rmse(prediction):
        error = np.sum((prediction[holdout]-target[holdout])**2,axis=1)
        return round(float(np.sqrt(np.average(error,weights=quality[holdout]))),4)

    if np.count_nonzero(holdout)<15:
        return None
    one_before = np.roll(target,1,axis=0)
    two_before = np.roll(target,2,axis=0)
    features = np.stack((one_before,two_before,drive),axis=-1)
    prediction = np.empty_like(target)
    parameters = []
    weights = quality[train,None]
    for i in range(2):
        training = features[train,i]
        beta = np.linalg.solve(training.T@(training*weights)+np.diag([.7,.7,1.5]),
                               training.T@(target[train,i]*weights[:,0]))
        prediction[:,i] = features[:,i]@beta
        parameters.append(beta.tolist())
    persistence, fitted = rmse(one_before),rmse(prediction)
    return {"arx":parameters, "persistence_rmse":persistence,
            "one_step_rmse":fitted,"improves_persistence":fitted<persistence}


def fit_models(series, drives, fps):
    """Estimate damped causal responses with disjoint time-ordered holdout."""
    count = len(series)
    split = round(count*.72)
    samples = np.arange(count)
    models = {}
    for key in sorted(set().union(*(row.keys() for row in series))):
        observed = np.asarray([row.get(key,[0.,0.,0.]) for row in series])
        quality, target = observed[:,2],observed[:,:2]
        drive = np.asarray([row.get(key,[0.,0.]) for row in drives])
        visible = (quality>.20)&np.asarray([key in row for row in drives])
        good = visible&np.r_[False,False,visible[:-2]]&np.r_[False,visible[:-1]]
        train, holdout = good&(samples<split),good&(samples>=split)
        n_train,n_test = np.count_nonzero(train),np.count_nonzero(holdout)
        if n_train<18:
            continue
        weights = quality[train,None]
        rigid_train = float(np.average(np.sum(target[train]**2,axis=1),weights=quality[train]))
        candidate = None
        for hz in (.8,1.15,1.6,2.2,3.05,4.25,5.8,7.4):
            for half in (.08,.14,.22,.32,.46):
                pole = np.exp2(-1/(fps*half))
                a1,a2 = 2*pole*np.cos(2*np.pi*hz/fps),-pole*pole
                unit = response(drive,visible,a1,a2)
                given = unit[train]
                # Passive inertial response starts opposite carrier
                # acceleration. Fit the projected response with shrinkage.
                gain = np.clip(np.sum(given*target[train]*weights,axis=0) /
                               (np.sum(given**2*weights,axis=0)+1.5),-2.,0.)
                prediction = unit*gain
                mse = float(np.average(np.sum((prediction[train]-target[train])**2,axis=1),
                                       weights=quality[train]))
                if candidate is None or mse<candidate[0]:
                    candidate = (mse,a1,a2,gain,prediction,hz,half)
        mse,a1,a2,gain,prediction,hz,half = candidate
        baseline_rmse = holdout_rmse = None
        if n_test:
            baseline_rmse = float(np.sqrt(np.average(np.sum(target[holdout]**2,axis=1),weights=quality[holdout])))
            holdout_rmse = float(np.sqrt(np.average(np.sum((prediction[holdout]-target[holdout])**2,axis=1),
                                                   weights=quality[holdout])))
        fit_supported = bool(n_test>=15 and baseline_rmse>.15 and holdout_rmse<baseline_rmse*.985)
        models[key] = {"ar":[float(a1),float(a2)],"drive":gain.tolist(),
                       "dominant_hz":hz,"half_life_seconds":half,
                       "settling_seconds":half*np.log2(20),
                       "train_samples":int(n_train),"test_samples":int(n_test),
                       "train_rigid_rmse":round(np.sqrt(rigid_train),4),
                       "train_rmse":round(np.sqrt(mse),4),
                       "baseline_rmse":round(baseline_rmse,4) if baseline_rmse is not None else None,
                       "holdout_rmse":round(holdout_rmse,4) if holdout_rmse is not None else None,
                       "amplitude_p90":round(float(np.quantile(np.linalg.norm(target[visible],axis=1),.9)),3),
                       "supported":fit_supported,
                       "inertial_lag_train":lag_diagnostic(target,drive,visible,split,fps),
                       "recorded_sequence":observed_sequence_scores(target,drive,quality,train,holdout)}
    return models,split


def rounded_frames(frames):
    return [{key:[round(value,3) for value in observation]
             for key,observation in row.items()} for row in frames]


def motion_study(source, timeline, region_file, factor):
    manifest = json.loads(timeline.read_text())
    regions = json.loads(region_file.read_text())["frames"]
    if len(regions)!=len(manifest["frames"]):
        raise ValueError("Region and video count mismatch")
    fps = manifest["fps"]
    flow = analyze_flow(source,manifest,timeline.parent,regions,factor)
    observations,inputs = displacement_series(flow,fps)
    frames,carrier = rounded_frames(observations),rounded_frames(inputs)
    models,split = fit_models(frames,carrier,fps)
    result = {"version":1,"fps":fps,"width":manifest["frames"][0][0],"height":manifest["height"],
              "method":"forward/backward DIS, foreground and texture gate, projected anatomical carrier",
              "frames":frames,"carrier":carrier,
              "models":models,
              "validation":{"chronological_split_frame":split,"measured_frames":sum(bool(f) for f in frames),
                            "supported_regions":sum(m["supported"] for m in models.values()),
                            "eligible_holdout_regions":sum(m["test_samples"]>=15 for m in models.values()),
                            "recorded_sequence_improves_persistence":sum(
                                bool(m["recorded_sequence"] and m["recorded_sequence"]["improves_persistence"])
                                for m in models.values()),
                            "fitted_regions":len(models),
                            "visible_region_frame_samples":sum(len(f) for f in frames)}}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command",required=True)
    for name,paths in (("world",("source","model","output")),
                       ("measure",("source","timeline","regions","output"))):
        command = commands.add_parser(name)
        for path in paths:
            command.add_argument(path,type=Path)
        if name=="measure":
            command.add_argument("--scale",type=float,default=.375)
    args = parser.parse_args()
    if args.command=="world":
        result = world_pose(args.source,args.model)
        report = {"monocular_3d_frames":sum(f is not None for f in result["frames"]),
                  "frames":len(result["frames"])}
    else:
        result = motion_study(args.source,args.timeline,args.regions,args.scale)
        report = result["validation"]
    write_json(result,args.output)
    print(json.dumps(report))


if __name__=="__main__":
    main()
