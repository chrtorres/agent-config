"""Render tracked shape and skin-tone edits to a new MP4 using Python."""
import argparse
import json
import math
from pathlib import Path

import av
import cv2
import numpy as np
from PIL import Image

from cleanup import compile_cleanup, displacement, reach
from progress import Progress
from soft_body import soft_body_track, with_offsets
from colors import LUMA, apply_colors, guided_hair, valid_colors
from cleanup_tracks import build_tracks
from face_fragments import audio_sample_durations, fragment_audio, merge
from media import inspect, presentation_offset, restore_audio_timing, uhd_size, upright_source, write_atomically
from point_regions import support, validate_points


def grade(rgb, skin, tone):
    light, warmth, saturation = tone
    color = rgb.astype(np.float32)/255
    y = color @ np.float32([.2126,.7152,.0722])
    y = y[..., None]
    midtones = 4*y*(1-y)
    delta = (color-y)*saturation*.42+midtones*(light*.16+warmth*np.float32([.085,.012,-.085]))
    mix = skin[..., None]*(np.clip(color+delta,0,1)-color)
    return np.rint((color+mix)*255).astype(np.uint8)


def bounded_remap(frame, matte, fields, *, clean=False, pins=None):
    bounds = []
    for shape, adjustment in fields:
        x,y,ux,uy,rx,ry = shape[:6]
        # The uniformly scaled part pushes its surroundings out to reach().
        outer = reach(adjustment)
        rx, ry = rx*outer+abs(shape[6] if len(shape) > 6 else 0), ry*outer+abs(shape[7] if len(shape) > 7 else 0)
        rw, rh = np.hypot(ux*rx,uy*ry)+4, np.hypot(uy*rx,ux*ry)+4
        bounds.append((x-rw,y-rh,x+rw,y+rh))
    height, width = frame.shape[:2]
    left, top = max(0,int(min(r[0] for r in bounds))), max(0,int(min(r[1] for r in bounds)))
    right, bottom = min(width,1+int(max(r[2] for r in bounds))), min(height,1+int(max(r[3] for r in bounds)))
    if right<=left or bottom<=top:
        return frame
    y,x = np.mgrid[top:bottom,left:right].astype(np.float32)
    sx,sy = x,y
    # Inverse sampling prevents gaps that forward splatting leaves on expansion.
    calculate = compile_cleanup(fields,pins) if clean else lambda x,y: displacement(x,y,fields)
    # The core scale can exceed 2x, so the plain fixed point x-d(s) is not
    # contractive there. Damped steps converge for both growth and shrinkage.
    expanded = any(max(adjustment) > .45 for _, adjustment in fields)
    for _ in range(24 if expanded else 14):
        dx,dy = calculate(sx,sy)
        if expanded:
            # Damping keeps the larger forward expansion contractive around
            # the support center during inverse sampling.
            sx,sy = sx+.6*(x-dx-sx), sy+.6*(y-dy-sy)
        else:
            sx,sy = x-dx,y-dy
    affected = np.hypot(sx-x,sy-y)>.045
    sampled = cv2.remap(frame,sx,sy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    alpha = cv2.remap(matte,sx,sy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)[...,None]
    roi = np.s_[top:bottom,left:right]
    clear = np.clip((matte[roi]-.015)/.125,0,1)
    clear = (clear**2*(3-2*clear))[...,None]
    # Inverse coordinates supply the original texture and its adjacent
    # background. The two mattes keep unrelated background unchanged.
    weight = np.maximum(clear,alpha)
    composite = np.rint(sampled*weight+frame[roi]*(1-weight)).astype(np.uint8)
    frame[roi][affected] = composite[affected]
    return frame


def follow_observation(stabilized, raw, observation):
    if raw is None or observation is None or observation[2] < .28:
        return stabilized
    result=[]
    for shape,original in zip(stabilized,raw):
        if shape is None or original is None:
            result.append(shape)
            continue
        dx,dy=original[0]-shape[0],original[1]-shape[1]
        size,motion=math.hypot(dx,dy),math.hypot(*observation[:2])
        if size<.02 or motion<.04:
            result.append(shape)
            continue
        alignment=(dx*observation[0]+dy*observation[1])/(size*motion)
        amount=.55*max(0,alignment)*min(1,observation[2]/.7,motion/size)
        result.append([shape[0]+dx*amount,shape[1]+dy*amount,*shape[2:]])
    return result


def render(source, timeline, region_file, skin_dir, target, shapes, tone, uhd, *, clean=False,
           cleanup_tracks=None, motion_study=None, points=None, physics=True, colors=None):
    manifest = json.loads(timeline.read_text())
    regions = json.loads(region_file.read_text())
    if len(manifest["frames"]) != len(regions["frames"]):
        raise ValueError("Shape regions and media timeline do not match")
    tracks=regions["frames"]
    pins=[]
    if clean:
        prepared=json.loads(cleanup_tracks.read_text()) if cleanup_tracks else build_tracks(regions,manifest)
        if prepared["version"]!=1 or len(prepared["frames"])!=len(tracks):
            raise ValueError("Cleanup tracks and media timeline do not match")
        tracks=prepared["frames"]
        pins=prepared.get("pins",[])
    measured=json.loads(motion_study.read_text())["frames"] if clean and motion_study else None
    if measured is not None and len(measured)!=len(tracks):
        raise ValueError("Motion study and media timeline do not match")
    points = {} if points is None else points
    validate_points(points, regions["parts"])
    if set(shapes)-regions["parts"].keys()-points.keys():
        raise ValueError("Unknown feature. Available features: "+", ".join(regions["parts"]))
    # Soft-tissue motion of the added volume, simulated once over the track
    # the edit follows. app/render.mjs uses the same tracks.
    dynamics = {key:soft_body_track(tracks,key,adjustment,manifest) for key,adjustment in shapes.items()
                if physics and key not in points and any(adjustment)}
    tw,th = manifest["tile"]
    grid = manifest["grid"]
    slots = grid**2
    size = (manifest["frames"][0][0],manifest["height"])
    shape_active = any(any(adjustment) for adjustment in shapes.values())
    tone_active = any(tone)
    colors = colors or {}
    areas = regions.get("colorAreas") or [None]*len(manifest["frames"])
    if len(areas) != len(manifest["frames"]):
        raise ValueError("Feature color areas and media timeline do not match")
    masks_needed = tone_active or "hair" in colors

    cv2.setNumThreads(2)
    if target.resolve()==source.resolve():
        raise ValueError("Choose an output path different from the source")

    def write(pending):
        expected_dimensions = uhd_size(*size) if uhd else size
        with upright_source(source) as upright, av.open(str(upright)) as clip:
            video = clip.streams.video[0]
            video.thread_count = 3
            audio = next(iter(clip.streams.audio), None)
            fragmented = audio is not None and video.frames == 0
            video_clock = video.time_base.denominator
            picture = pending.with_name("picture.mp4") if fragmented else pending
            options = {
                "movflags": "+frag_keyframe+delay_moov+default_base_moof" if fragmented else "+faststart",
                "video_track_timescale": str(video_clock), "movie_timescale": str(video_clock),
            }
            count = 0
            progress = Progress()
            with av.open(str(picture), mode="w", options=options) as result:
                stream = result.add_stream("libx264rgb", rate=video.average_rate or 30,
                                           options={"crf":"0", "preset":"ultrafast", "tune":"zerolatency"})
                stream.width, stream.height = expected_dimensions
                stream.pix_fmt = "rgb24"
                stream.thread_count = 4
                stream.time_base = stream.codec_context.time_base = video.time_base
                stream.codec_context.colorspace = 0
                stream.codec_context.color_range = 2
                stream.codec_context.color_primaries = 1
                stream.codec_context.color_trc = 13
                audio_out = result.add_stream_from_template(audio) if audio is not None and not fragmented else None
                for packet in clip.demux(video, *([audio] if audio_out is not None else [])):
                    if packet.stream.type == "audio":
                        if packet.size:
                            packet.stream = audio_out
                            result.mux(packet)
                        continue
                    for frame in packet.decode():
                        index = count
                        count += 1
                        progress.update(index, len(tracks))
                        if index >= len(tracks):
                            raise ValueError("Source contains more frames than the prepared timeline.")
                        if abs(float(frame.pts*frame.time_base)-manifest.get("presentationStart",0)-
                               presentation_offset(manifest,index)) > .0006:
                            raise ValueError(f"Timeline mismatch at frame {index}")
                        page,slot = divmod(index,slots)
                        if slot==0:
                            if shape_active:
                                matte_name = manifest["pages"][page][0]
                                matte_atlas = np.array(Image.open(timeline.parent/matte_name))
                            if masks_needed:
                                skin_atlas = np.array(Image.open(skin_dir/f"skin-{page:03d}.png"))
                                # Pages are RGB (red skin, green hair); older pages are skin only.
                                # Pages without a blue lightness guide upsample hair bilinearly.
                                if skin_atlas.ndim == 2:
                                    skin_atlas = np.dstack([skin_atlas, np.zeros_like(skin_atlas)])
                                if skin_atlas.shape[2] == 2:
                                    skin_atlas = np.dstack([skin_atlas, np.zeros_like(skin_atlas[...,0])])
                        x,y = slot%grid*tw,slot//grid*th
                        tile = np.s_[y:y+th,x:x+tw]
                        rgb = frame.to_ndarray(format="rgb24")
                        # The hair guide compares against the frame's own lightness, before any grade.
                        luma = (rgb.astype(np.float32)/255) @ LUMA if "hair" in colors else None
                        if tone_active:
                            skin = cv2.resize(skin_atlas[tile][...,0],size,interpolation=cv2.INTER_LINEAR)/np.float32(255)
                            rgb = grade(rgb,skin,tone)
                        if colors:
                            hair = guided_hair(skin_atlas[tile],size,manifest["pixelScale"],luma) \
                                if "hair" in colors else None
                            rgb = apply_colors(rgb,colors,hair,areas[index])
                        if shape_active:
                            def supports(key):
                                if key in points:
                                    field = support(points[key], regions["frames"][index])
                                    if field is None:
                                        return ()
                                    px,py = field[:2]
                                    if not (0 <= px < size[0] and 0 <= py < size[1]):
                                        return ()
                                    matte_tile=matte_atlas[tile]
                                    col=min(tw-1,int(px/manifest["pixelScale"]))
                                    row=min(th-1,int(py/manifest["pixelScale"]))
                                    return (field,) if matte_tile[row,col,0] > 65 else ()
                                area=tracks[index].get(key,[])
                                area=follow_observation(area,regions["frames"][index].get(key),measured[index].get(key)) if measured else area
                                return with_offsets(area,dynamics[key][index]) if dynamics.get(key) else area
                            fields = [(field,adjustment) for key,adjustment in shapes.items() if any(adjustment)
                                      for field in supports(key) if field is not None]
                            if fields:
                                matte = cv2.resize(matte_atlas[tile][...,0],size,interpolation=cv2.INTER_LINEAR)/np.float32(255)
                                anchors = {id(shapes[key]):value for key,value in pins[index].items() if key in shapes} if pins else None
                                rgb = bounded_remap(rgb,matte,fields,clean=clean,pins=anchors)
                        if uhd:
                            rgb = cv2.resize(rgb, expected_dimensions, interpolation=cv2.INTER_LANCZOS4)
                        timed = av.VideoFrame.from_ndarray(rgb, format="rgb24")
                        timed.pts, timed.time_base = frame.pts, frame.time_base
                        # Zero-latency encoding lets the packet retain its source frame's own duration.
                        for encoded in stream.encode(timed):
                            if fragmented:
                                encoded.dts -= video.start_time or 0
                            encoded.duration = frame.duration
                            result.mux(encoded)
                for packet in stream.encode():
                    result.mux(packet)
            if count != len(tracks):
                raise ValueError("Edited video encoding did not retain every frame.")
            if fragmented:
                sound = pending.with_name("sound.mp4")
                durations = audio_sample_durations(upright)
                fragment_audio(upright, sound, durations, video_clock)
                merge(picture, sound, pending, video_clock, audio.time_base.denominator)
                if audio_sample_durations(pending) != durations:
                    raise ValueError("Edited export changed audio sample durations.")
            original = inspect(upright, not fragmented)
            edited = inspect(pending, not fragmented)
            if audio is not None and not fragmented and edited[3:] != original[3:]:
                restore_audio_timing(upright, pending)
                edited = inspect(pending)
            if edited[1:] != original[1:]:
                raise ValueError("Edited export changed frame timing or audio.")

    write_atomically(target,write)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source","timeline","regions","skin_directory","output"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--shape",nargs=3,metavar=("FEATURE","WIDTH_PERCENT","HEIGHT_PERCENT"),action="append",default=[])
    parser.add_argument("--tone",nargs=3,type=float,metavar=("LIGHTNESS","WARMTH","SATURATION"),default=None)
    parser.add_argument("--settings",type=Path,help="JSON settings downloaded from the review")
    parser.add_argument("--uhd",action="store_true")
    parser.add_argument("--cleanup-tracks", type=Path, help="Prepared joint-relative cleanup tracks")
    parser.add_argument("--motion-study",type=Path,help="Use measured source motion with Clean image")
    parser.add_argument("--clean",action="store_true",help="Smooth interacting shape adjustments")
    args=parser.parse_args()
    try:
        recipe = json.loads(args.settings.read_text()) if args.settings else {"version":1,"shapes":{},"tone":[0,0,0]}
        if recipe["version"] != 1:
            raise ValueError("Unsupported settings version")
        cleanup = recipe.get("cleanup",False)
        physics = recipe.get("physics",True)
        if not isinstance(physics,bool):
            raise ValueError("Physics setting must be true or false")
        recorded = recipe.get("recordedDynamics",False)
        if not isinstance(recorded,bool):
            raise ValueError("Recorded dynamics setting must be true or false")
        if recorded and args.motion_study is None:
            raise ValueError("This recipe requires --motion-study")
        if not isinstance(cleanup,bool):
            raise ValueError("Cleanup setting must be true or false")
        shapes = {key:(float(width)/100,float(height)/100) for key,(width,height) in recipe["shapes"].items()}
        points = recipe.get("points",{})
        validate_points(points, json.loads(args.regions.read_text())["parts"])
        shapes.update({key:(float(width)/100,float(height)/100) for key,width,height in args.shape})
        colors = valid_colors(recipe.get("colors"))
        tone = [float(value) for value in recipe["tone"]]
        if len(tone) != 3:
            raise ValueError("Expected three tone values")
        if args.tone is not None:
            tone = args.tone
    except (KeyError, OSError, ValueError, TypeError, AttributeError) as error:
        parser.error(f"Invalid edit settings: {error}")
    if not all(-.70<=v<=1.10 for values in shapes.values() for v in values):
        parser.error("Shape percentages must be between -70 and 110.")
    if not all(abs(value)<=maximum for value,maximum in zip(tone,[45,40,40])):
        parser.error("Tone out of range. Limits are ±45 lightness, ±40 warmth and ±40 saturation.")
    if not any(tone) and not any(any(v) for v in shapes.values()) and not colors:
        parser.error("Provide at least one nonzero shape, tone, or color adjustment.")
    render(args.source,args.timeline,args.regions,args.skin_directory,args.output,
           shapes,[value/100 for value in tone],args.uhd,clean=args.clean or cleanup,cleanup_tracks=args.cleanup_tracks,
           motion_study=args.motion_study,points=points,physics=physics,colors=colors)
