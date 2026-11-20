"""Stabilize editable supports in their observed anatomical reference frames."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from anatomy import detail_anchors
from cleanup_axial import axial_anchors
from cleanup_lower import lower_anchors
from cleanup_upper import upper_anchors


def basis(anchor):
    ax,ay,bx,by = anchor
    dx,dy = bx-ax,by-ay
    length = math.hypot(dx,dy)
    if length<7 or not math.isfinite(length):
        return None
    return ax,ay,dx/length,dy/length,length


def to_local(shape, frame):
    x,y,ux,uy,rx,ry = shape
    ax,ay,ex,ey,length = frame
    dx,dy = x-ax,y-ay
    orientation = math.atan2(ex*uy-ey*ux,ex*ux+ey*uy)
    return ((dx*ex+dy*ey)/length, (dy*ex-dx*ey)/length,
            math.log(rx/length),math.log(ry/length),orientation)


def axis_angle_difference(a,b):
    # An ellipse has the same support if both of its axes are reversed.
    return (a-b+math.pi/2)%math.pi-math.pi/2


def bounded(value, limit):
    return max(-limit,min(limit,value))


def stabilize(series, index, radius):
    shape, frame, center = series[index]
    ax,ay,ex,ey,length = frame
    minor = min(shape[-2:])/length
    samples = [(0,1.,(0.,)*5)]
    sides = set()
    for sign in (-1,1):
        for step in range(1,radius+1):
            at=index+sign*step
            if not 0<=at<len(series) or series[at] is None:
                break
            _,other_frame,other=series[at]
            if max(other_frame[-1],length)/min(other_frame[-1],length)>1.45:
                break
            delta=tuple(b-a for a,b in zip(center[:4],other[:4])) + (axis_angle_difference(other[4],center[4]),)
            # Allow fast observed rotation or flexion to pass through. The
            # residual relative to the current bone determines admissibility.
            error=max(math.hypot(*delta[:2])/max(.055,minor*.58), max(abs(v) for v in delta[2:4])/.32,
                      abs(delta[4])/.62)
            if error>=1:
                break
            weight=(1-error**2)**2 * math.exp(-.34*step*step)
            if weight<.018:
                break
            samples.append((sign*step,weight,delta))
            sides.add(sign)
    if len(sides)<2:
        return shape
    total=sum(weight for _,weight,_ in samples)
    slope=sum(t*weight for t,weight,_ in samples)
    moment=sum(t*t*weight for t,weight,_ in samples)
    denominator=total*moment-slope*slope
    if denominator<1e-8:
        return shape
    # Evaluate the local linear fit at t=0. A uniform real movement is
    # reproduced at its recorded time, even with asymmetric confidence.
    intercepts=[sum(weight*(moment-slope*t)*delta[k] for t,weight,delta in samples)/denominator
                for k in range(5)]
    limit=min(7.,min(shape[-2:])*.22)/length
    local_x=center[0]+bounded(intercepts[0],limit)
    local_y=center[1]+bounded(intercepts[1],limit)
    angle=math.atan2(ey,ex)+center[4]+bounded(intercepts[4],.14)
    rx=length*math.exp(center[2]+bounded(intercepts[2],.115))
    ry=length*math.exp(center[3]+bounded(intercepts[3],.115))
    return [round(value,3) for value in (
        ax+length*(local_x*ex-local_y*ey),ay+length*(local_x*ey+local_y*ex),
        math.cos(angle),math.sin(angle),rx,ry)]


def limb_pins(points,regions,width,height):
    result={}
    for side,offset in (("left",0),("right",1)):
        arm=(11+offset,13+offset,15+offset)
        lower=(25+offset,27+offset,29+offset,31+offset)
        for key,ids in ((f"{side}-arm",arm),(f"{side}-hand",arm[-1:]),
                        (f"{side}-leg",(23+offset,*lower)),(f"{side}-calf",lower)):
            supports=[shape for shape in regions.get(key,[]) if shape is not None]
            if not supports:
                continue
            radius=round(max(5,min(18,.46*min(min(s[-2:]) for s in supports))),3)
            for id in ids:
                point=points.get(id)
                if point and point[2]>=46 and 0<=point[0]<width and 0<=point[1]<height:
                    result.setdefault(key,[]).append([point[0],point[1],radius])
    return result


def build_tracks(source, manifest):
    raw=source["frames"]
    if len(raw)!=len(manifest["frames"]):
        raise ValueError("Cleanup regions and pose timeline have different frame counts")
    output=[dict(row) for row in raw]
    pins=[{} for _ in raw]
    changes=Counter()
    radius=max(2,min(4,round(manifest["fps"]*.08)))
    for start,stop in manifest["shots"]:
        local={}
        for index in range(start,stop):
            values=manifest["frames"][index][1][0]
            points={key:(x/4,y/4,confidence)
                    for key,(x,y,confidence) in zip(manifest["landmarks"],values)}
            regions=raw[index]
            pins[index]=limb_pins(points,regions,manifest["frames"][index][0],manifest["height"])
            references=upper_anchors(points,regions)|lower_anchors(points,regions)|axial_anchors(points,regions)
            references.update(detail_anchors(points,regions,source.get("parents",{}),references))
            for key,references_by_slot in references.items():
                for slot,(shape,anchor) in enumerate(zip(regions.get(key,[]),references_by_slot)):
                    if shape is None or anchor is None:
                        continue
                    frame=basis(anchor)
                    if frame is not None:
                        track=local.setdefault((key,slot),[None]*(stop-start))
                        track[index-start]=(shape,frame,to_local(shape,frame))
        for (key,slot),series in local.items():
            for index,sample in enumerate(series):
                if sample is None:
                    continue
                shape=stabilize(series,index,radius)
                if shape!=sample[0] and (key in {"mouth","chin","left-thumb","right-thumb","left-pinky","right-pinky"}
                                          or "finger" in key):
                    shape=[original+(filtered-original)*.65 for original,filtered in zip(sample[0],shape)]
                    length=math.hypot(*shape[2:4])
                    shape[2],shape[3]=shape[2]/length,shape[3]/length
                    shape=[round(value,3) for value in shape]
                if shape!=sample[0]:
                    row=output[start+index]
                    if row[key] is raw[start+index][key]:
                        row[key]=row[key].copy()
                    row[key][slot]=shape
                    changes[key]+=1
    return {"version":1,"model":"projected-joint-frames","frames":output,"pins":pins,
            "stabilized_samples":dict(changes)}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("regions","timeline","output"):
        parser.add_argument(arg,type=Path)
    args=parser.parse_args()
    result=build_tracks(json.loads(args.regions.read_text()),json.loads(args.timeline.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    staging=args.output.with_suffix(".partial")
    staging.write_text(json.dumps(result,separators=(",",":")))
    staging.replace(args.output)
    print(json.dumps({"frames":len(result["frames"]),"stabilized_samples":result["stabilized_samples"]}))
