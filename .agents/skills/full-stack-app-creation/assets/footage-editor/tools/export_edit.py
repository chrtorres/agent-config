"""Render tracked shape and skin-tone edits to a new MP4 using Python."""
import argparse
import json
import math
from pathlib import Path
import subprocess

import av
import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image

from cleanup import compile_cleanup
from cleanup_tracks import build_tracks
from media import restore_audio_timing, write_atomically
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


def displacement(x, y, fields):
    dx, dy = np.zeros_like(x), np.zeros_like(y)
    for (cx,cy,ux,uy,rx,ry), (width,height) in fields:
        a = (x-cx)*ux+(y-cy)*uy
        b = (y-cy)*ux-(x-cx)*uy
        fade = np.maximum(0,1-(a/rx)**2-(b/ry)**2)**2
        dx += (a*width*ux-b*height*uy)*fade
        dy += (a*width*uy+b*height*ux)*fade
    return dx, dy


def bounded_remap(frame, matte, fields, *, clean=False, pins=None):
    bounds = []
    for (x,y,ux,uy,rx,ry), _ in fields:
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
    expanded = any(max(adjustment) > .75 for _, adjustment in fields)
    for _ in range(16 if expanded else 9):
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
           cleanup_tracks=None, motion_study=None, points=None):
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
    tw,th = manifest["tile"]
    grid = manifest["grid"]
    slots = grid**2
    size = (manifest["frames"][0][0],manifest["height"])
    shape_active = any(any(adjustment) for adjustment in shapes.values())
    tone_active = any(tone)

    cv2.setNumThreads(2)
    if target.resolve()==source.resolve():
        raise ValueError("Choose an output path different from the source")

    def write(pending):
        filters = ["-vf","scale=2160:3840:flags=lanczos"] if uhd else []
        arguments = [imageio_ffmpeg.get_ffmpeg_exe(),"-hide_banner","-nostdin","-loglevel","error",
                     "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{size[0]}x{size[1]}",
                     "-framerate",str(manifest["fps"]),"-i","pipe:0","-i",str(source),"-map","0:v:0",
                     "-map","1:a:0",*filters,"-c:v","libx264","-threads:v","4","-filter_threads","2",
                     "-preset","ultrafast","-crf","16","-pix_fmt","yuv420p","-c:a","copy",
                     "-movflags","+faststart",str(pending)]
        with av.open(str(source)) as clip, subprocess.Popen(arguments,stdin=subprocess.PIPE) as encoder:
            count = 0
            try:
                for index, frame in enumerate(clip.decode(video=0)):
                    count = index+1
                    if abs(float(frame.pts*frame.time_base)-index/manifest["fps"])>.0006:
                        raise ValueError(f"Timeline mismatch at frame {index}")
                    page,slot = divmod(index,slots)
                    if slot==0:
                        if shape_active:
                            matte_name = manifest["pages"][page][0]
                            matte_atlas = np.array(Image.open(timeline.parent/matte_name))
                        if tone_active:
                            skin_atlas = np.array(Image.open(skin_dir/f"skin-{page:03d}.png"))
                    x,y = slot%grid*tw,slot//grid*th
                    tile = np.s_[y:y+th,x:x+tw]
                    rgb = frame.to_ndarray(format="rgb24")
                    if tone_active:
                        skin = cv2.resize(skin_atlas[tile],size,interpolation=cv2.INTER_LINEAR)/np.float32(255)
                        rgb = grade(rgb,skin,tone)
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
                            return follow_observation(area,regions["frames"][index].get(key),measured[index].get(key)) if measured else area
                        fields = [(field,adjustment) for key,adjustment in shapes.items() if any(adjustment)
                                  for field in supports(key) if field is not None]
                        if fields:
                            matte = cv2.resize(matte_atlas[tile][...,0],size,interpolation=cv2.INTER_LINEAR)/np.float32(255)
                            anchors = {id(shapes[key]):value for key,value in pins[index].items() if key in shapes} if pins else None
                            rgb = bounded_remap(rgb,matte,fields,clean=clean,pins=anchors)
                    encoder.stdin.write(rgb.tobytes())
            finally:
                encoder.stdin.close()
            if encoder.wait() or count!=len(regions["frames"]):
                raise ValueError("Edited video encoding did not complete")
        restore_audio_timing(source,pending)

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
    if not any(tone) and not any(any(v) for v in shapes.values()):
        parser.error("Provide at least one nonzero shape or tone adjustment.")
    render(args.source,args.timeline,args.regions,args.skin_directory,args.output,
           shapes,[value/100 for value in tone],args.uhd,clean=args.clean or cleanup,cleanup_tracks=args.cleanup_tracks,
           motion_study=args.motion_study,points=points)
