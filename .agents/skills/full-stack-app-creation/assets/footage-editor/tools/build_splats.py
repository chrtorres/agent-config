"""Build a measured-view, time-conditioned Gaussian representation from a clip.

Tracked visible texture observations are represented as local Gaussians in
(x,y,z,t). Depth is a monocular pose estimate. The captured view is the
projection domain; no surface is extended behind an occlusion.
"""
import argparse
import base64
import json
from pathlib import Path
import tempfile

import av
import cv2
import numpy as np


LINKS = ((0, 7), (0, 8), (7, 11), (8, 12), (11, 12), (11, 13), (13, 15),
         (12, 14), (14, 16), (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
         (24, 26), (26, 28), (27, 29), (27, 31), (28, 30), (28, 32))
FORMAT = "source-gaussians-4d"
RECORD = np.dtype([("id", "<u4"), ("parameters", "<f4", 9), ("rgba", "u1", 4)])
TIME_SIGMA_FRAMES = .78


class Mattes:
    def __init__(self, timeline, metadata):
        self.directory = timeline.parent
        self.metadata = metadata
        self.current = None
        self.atlas = None

    def at(self, index, size):
        grid = self.metadata["grid"]
        cols, rows = self.metadata["tile"]
        page, slot = divmod(index, grid*grid)
        if page != self.current:
            path = self.directory / self.metadata["pages"][page][0]
            atlas = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if atlas is None:
                raise ValueError(f"Failed to read foreground matte {path.name}")
            self.atlas = atlas[..., 2]
            self.current = page
        x, y = slot % grid * cols, slot // grid * rows
        return cv2.resize(self.atlas[y:y+rows, x:x+cols], size, interpolation=cv2.INTER_LINEAR)


def sample(image, xy):
    if not len(xy):
        return np.empty((0,) + image.shape[2:], dtype=image.dtype)
    return cv2.remap(image, xy[:, 0:1], xy[:, 1:2], cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE)[:, 0]


def advect(previous_image, image, points, matte):
    """Follow existing observations and discard lost or inconsistent tracks."""
    empty = np.empty(0, dtype=np.int64)
    if previous_image is None or not len(points):
        return empty, np.empty((0, 2), dtype=np.float32)
    options = {"winSize": (17, 17), "maxLevel": 3,
               "criteria": (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 14, .02)}
    start = points.reshape((-1, 1, 2))
    forward, good, error = cv2.calcOpticalFlowPyrLK(previous_image, image, start, None, **options)
    if forward is None:
        return empty, np.empty((0, 2), dtype=np.float32)
    reverse, back, _ = cv2.calcOpticalFlowPyrLK(image, previous_image, forward, None, **options)
    if reverse is None:
        return empty, np.empty((0, 2), dtype=np.float32)
    xy = forward[:, 0]
    consistency = np.linalg.norm(reverse[:, 0] - points, axis=1)
    height, width = image.shape
    visible = ((xy[:, 0] >= 0) & (xy[:, 0] < width-1)
               & (xy[:, 1] >= 0) & (xy[:, 1] < height-1))
    keep = (good[:, 0] > 0) & (back[:, 0] > 0) & visible & (consistency < 1.1) & (error[:, 0] < 33)
    indexes = np.flatnonzero(keep)
    indexes = indexes[sample(matte, xy[indexes]) >= 105]
    # Retain the oldest ID when two observations converge on the same patch.
    _, unique = np.unique((xy[indexes]//3).astype(np.int32), return_index=True, axis=0)
    indexes = indexes[np.sort(unique)]
    return indexes, xy[indexes]


def replenish(matte, xy, step, budget, frame):
    """Seed newly visible gaps without moving existing optical-flow tracks."""
    height, width = matte.shape
    if budget <= 0:
        return np.empty((0, 2), dtype=np.float32)
    occupied = np.full_like(matte, 255)
    for x, y in np.rint(xy).astype(int):
        occupied[y, x] = 0
    distances = cv2.distanceTransform(occupied, cv2.DIST_L2, 3) if len(xy) else occupied
    # A deterministic phase stagger avoids gaps perpetually falling between cells.
    offset = frame % 4
    y, x = np.mgrid[step//2 + (offset//2):height:step, step//2 + (offset%2):width:step]
    where = (matte[y, x] >= 134) & (distances[y, x] >= .67*step)
    candidates = np.column_stack((x[where], y[where])).astype(np.float32)
    if len(candidates) > budget:
        use = np.linspace(0, len(candidates)-1, budget).astype(int)
        candidates = candidates[use]
    return candidates


def relative_depth(xy, pose2d, pose3d, ids):
    """Interpolate visible MediaPipe world-z samples along nearby image bones."""
    bones = []
    index_for = {joint: index for index, joint in enumerate(ids)}
    for a, b in LINKS:
        if a not in index_for or b not in index_for:
            continue
        ax, ay, ac = pose2d[index_for[a]]
        bx, by, bc = pose2d[index_for[b]]
        az, bz = pose3d[a][2], pose3d[b][2]
        confidence = min(ac/100, bc/100, pose3d[a][3], pose3d[b][3])
        if confidence > .22 and np.isfinite(az+bz):
            bones.append(((ax/4, ay/4), (bx/4, by/4), az, bz, confidence))
    if not bones:
        return np.zeros(len(xy), dtype=np.float32), False

    left, right, back, front, confidence = map(np.array, zip(*bones))
    direction = right-left
    offset = xy[:, None, :]-left
    fractions = np.clip((offset*direction).sum(axis=2)
                        / np.maximum(1, (direction**2).sum(axis=1)), 0, 1)
    distance = ((offset-fractions[..., None]*direction)**2).sum(axis=2)
    closest = np.argpartition(distance, min(2, len(bones)-1), axis=1)[:, :3]
    selected = np.take_along_axis(distance, closest, axis=1)
    weight = confidence[closest]*np.exp(-(selected-selected.min(axis=1, keepdims=True))/1100)
    z = np.take_along_axis(back + fractions*(front-back), closest, axis=1)
    return np.clip((z*weight).sum(axis=1)/weight.sum(axis=1), -1.2, 1.2).astype(np.float32), True


def conditioned(rows, frame):
    """Mirror the browser's conditional centers for the projection check."""
    decode = lambda index: np.frombuffer(base64.b64decode(rows[index]), dtype=RECORD)
    center = decode(frame).copy()
    weighted = center["parameters"][:, :3].astype(float)
    total = np.ones((len(center), 1))
    for dt in (-2, -1, 1, 2):
        if not 0 <= frame+dt < len(rows):
            continue
        neighbor = decode(frame+dt)
        _, a, b = np.intersect1d(center["id"], neighbor["id"], assume_unique=True, return_indices=True)
        observed = neighbor["parameters"][b]
        weight = float(np.exp(-.5*(dt/TIME_SIGMA_FRAMES)**2))
        weighted[a] += (observed[:, :3]-dt*observed[:, 3:6])*weight
        total[a] += weight
    center["parameters"][:, :3] = weighted/total
    return center


def projection_fit(records, photo, matte, ratio):
    """Evaluate the RGB/alpha projector on observed frames used by the asset."""
    height, width = matte.shape
    accum = np.zeros((height, width, 4), dtype=np.float32)
    for item in records[np.argsort(-records["parameters"][:, 2], kind="stable")]:
        x,y,_,_,_,_,sx,sy,angle = item["parameters"]
        x,y,sx,sy = x/ratio[0],y/ratio[1],sx/ratio[0],sy/ratio[1]
        radius = max(sx,sy)*3
        l,r = max(0,int(x-radius)),min(width,int(x+radius+1))
        t,b = max(0,int(y-radius)),min(height,int(y+radius+1))
        if l>=r or t>=b:
            continue
        yy,xx = np.ogrid[t:b,l:r]
        u = ((xx-x)*np.cos(angle)+(yy-y)*np.sin(angle))/sx
        v = ((yy-y)*np.cos(angle)-(xx-x)*np.sin(angle))/sy
        alpha = np.exp(-.5*(u*u+v*v))[..., None]*item["rgba"][3]/255
        view=accum[t:b,l:r]
        view[..., :3] = view[..., :3]*(1-alpha)+item["rgba"][:3]*alpha
        view[..., 3:] = view[..., 3:]*(1-alpha)+alpha
    mask = matte >= 134
    predicted=accum[..., 3] >= .46
    overlap=mask & predicted
    union=mask | predicted
    color=accum[overlap, :3]/accum[overlap, 3:4]
    error=np.abs(photo[overlap].astype(float)-color)
    return {"silhouette_iou":float(overlap.sum()/max(1,union.sum())),
            "interior_rgb_mae":float(error.mean()) if error.size else None}


def build(source, timeline, world, output, report=None, step=7, max_points=1450):
    meta = json.loads(timeline.read_text())
    depth_data = json.loads(world.read_text()) if world else None
    if depth_data and (depth_data.get("version") != 1 or abs(depth_data["fps"]-meta["fps"]) > .001):
        raise ValueError("World pose and matte timelines differ in frame cadence")
    poses3d = depth_data["frames"] if depth_data else [None]*len(meta["frames"])
    if len(poses3d) != len(meta["frames"]):
        raise ValueError("World pose and matte timelines differ in frame count")
    cv2.setNumThreads(2)
    mattes=Mattes(timeline,meta)
    rows, counts, predictions, static_errors, fit_frames = [], [], [], [], []
    next_id=0
    depth_frames=0
    heldout_start=int(len(meta["frames"])*.8)
    old_gray=None
    old_points=np.empty((0,2),dtype=np.float32)
    old_records=np.empty(0,dtype=RECORD)
    old_ages=np.empty(0,dtype=int)

    with av.open(str(source)) as video:
        stream=video.streams.video[0]
        width,height=stream.width,stream.height
        size=(width//2,height//2)
        ratio=np.array([width/size[0],height/size[1]],dtype=np.float32)
        for frame_index, frame in enumerate(video.decode(stream)):
            if frame_index>=len(meta["frames"]):
                raise ValueError("Source exceeds the region timeline")
            if abs(float(frame.pts * frame.time_base) - frame_index/meta["fps"]) > .002:
                raise ValueError("Splat observations require the declared constant frame clock")
            rgb=cv2.resize(frame.to_ndarray(format="rgb24"), size, interpolation=cv2.INTER_AREA)
            gray=cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            matte=mattes.at(frame_index,size)
            old_index,tracked=advect(old_gray,gray,old_points,matte)
            birth=replenish(matte,tracked,step,max_points-len(tracked),frame_index)
            points=np.concatenate((tracked,birth))
            native=points*ratio
            records=np.zeros(len(points),dtype=RECORD)
            n=len(tracked)
            records["id"][:n]=old_records["id"][old_index]
            records["id"][n:]=np.arange(next_id,next_id+len(birth),dtype=np.uint32)
            next_id+=len(birth)
            params=records["parameters"]
            params[:, :2]=native
            pose=meta["frames"][frame_index][1]
            if len(points) and pose and poses3d[frame_index] is not None:
                params[:, 2], used = relative_depth(native,pose[0],poses3d[frame_index],meta["landmarks"])
                depth_frames+=used
            params[:n, 3:6]=params[:n, :3]-old_records["parameters"][old_index, :3]
            sigma=(step*float(ratio.mean()))*.43
            smooth=cv2.GaussianBlur(matte,(5,5),1)
            gx=sample(cv2.Sobel(smooth,cv2.CV_32F,1,0),points)
            gy=sample(cv2.Sobel(smooth,cv2.CV_32F,0,1),points)
            edge=np.clip(np.hypot(gx,gy)/420,0,1)
            params[:, 6]=sigma*(1+edge*.19)
            params[:, 7]=sigma*(1-edge*.43)
            params[:, 8]=np.arctan2(gy,gx)+np.pi/2
            records["rgba"][:, :3]=sample(rgb,points)
            records["rgba"][:, 3]=np.rint(sample(matte,points)*.96).astype(np.uint8)
            if frame_index>=heldout_start and n:
                paired=old_ages[old_index]>=2
                prior=old_records["parameters"][old_index[paired]]
                truth=params[:n, :2][paired]
                predictions.extend(np.linalg.norm(truth-prior[:, :2]-prior[:, 3:5],axis=1))
                static_errors.extend(np.linalg.norm(truth-prior[:, :2],axis=1))
            if len(records) and frame_index%max(1,len(meta["frames"])//14)==0:
                fit_frames.append((frame_index,rgb,matte))
            rows.append(base64.b64encode(records.tobytes()).decode("ascii"))
            counts.append(len(records))
            old_gray,old_points,old_records=gray,points,records
            old_ages=np.concatenate((old_ages[old_index]+1,np.ones(len(birth),dtype=int)))

    if len(rows)!=len(meta["frames"]):
        raise ValueError("Source and region timeline differ in frame count")
    fits=[projection_fit(conditioned(rows,index),rgb,matte,ratio) for index,rgb,matte in fit_frames]
    distribution=lambda values:{"median":float(np.median(values)),
                                "p90":float(np.percentile(values,90))} if len(values) else None
    metrics={"frames":len(rows),"depth_conditioned_frames":depth_frames,
             "samples_per_frame":distribution(counts),"distinct_track_ids":next_id,
             "projection_sample_frames":len(fits),
             "projection_time_conditioned":True,
             "measured_view_silhouette_iou":distribution([f["silhouette_iou"] for f in fits]),
             "measured_view_rgb_mae":distribution([f["interior_rgb_mae"] for f in fits
                                                   if f["interior_rgb_mae"] is not None]),
             "chronological_holdout_first_frame":heldout_start,
             "holdout_track_pair_count":len(predictions),
             "holdout_linear_prediction_error_px":distribution(predictions),
             "holdout_no_motion_error_px":distribution(static_errors)}
    payload={"version":1,"format":FORMAT,"width":width,"height":height,"fps":meta["fps"],
             "recordBytes":RECORD.itemsize,"temporalSigmaFrames":TIME_SIGMA_FRAMES,
             "depth":"monocular-pose-relative" if depth_frames else "planar",
             "frames":rows}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",encoding="ascii",dir=output.parent,delete=False) as temporary:
        json.dump(payload,temporary,separators=(",",":"))
        staging=Path(temporary.name)
    staging.replace(output)
    if report:
        report.write_text(json.dumps(metrics,indent=2)+"\n")
    print(json.dumps(metrics,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("timeline",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--world",type=Path,help="MediaPipe world pose track on the same clock")
    parser.add_argument("--report",type=Path)
    parser.add_argument("--step",type=int,default=7,help="Grid spacing in half-resolution pixels")
    parser.add_argument("--max-points",type=int,default=1450)
    args=parser.parse_args()
    if args.step<3 or args.max_points<1:
        parser.error("Step must be at least 3 pixels and budget positive")
    build(args.source,args.timeline,args.world,args.output,args.report,args.step,args.max_points)
