"""Generate a synthetic articulated recording and its shot-local matte atlas."""
from argparse import ArgumentParser
from fractions import Fraction
from pathlib import Path
import json
import math
from tempfile import TemporaryDirectory

import av
import numpy as np
from PIL import Image, ImageDraw

HEIGHT, WIDE, GRID, SCALE = 480, 544, 8, 8
TW, TH = WIDE // SCALE, HEIGHT // SCALE
POINTS = {0:(0,-150),7:(-14,-153),8:(14,-153),11:(-29,-111),12:(29,-111),
          13:(-51,-76),14:(51,-76),15:(-66,-46),16:(66,-46),23:(-21,-49),24:(21,-49),
          25:(-28,5),26:(28,5),27:(-35,54),28:(35,54),29:(-40,55),30:(39,55),
          31:(-24,61),32:(51,61)}
BONES = [(11,12),(23,24),(11,23),(12,24),(11,13),(12,14),(13,15),(14,16),
         (23,25),(24,26),(25,27),(26,28),(27,31),(28,32)]


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    assets=out/"timeline"
    assets.mkdir(exist_ok=True)
    mask_atlas=Image.new("RGB",(TW*GRID,TH*GRID))
    fill_atlas=mask_atlas.copy()
    poses=[]
    packets=[]
    for shot,width in enumerate((480,WIDE,480)):
        encoder=av.CodecContext.create("libx264","w")
        encoder.width,encoder.height,encoder.pix_fmt=width,HEIGHT,"yuv420p"
        encoder.time_base=Fraction(1,30)
        encoder.framerate=30
        encoder.options={"qp":"0","preset":"ultrafast","x264-params":"repeat-headers=1:bframes=0:keyint=12"}
        for local in range(16):
            frame=16*shot+local
            clean=Image.new("RGB",(WIDE,HEIGHT),("#272c40","#242f34","#293545")[shot])
            guide=ImageDraw.Draw(clean)
            for row in range(0,HEIGHT,24): guide.line((0,row,WIDE,row),fill="#485665")
            guide.rectangle((18,16,118,58),fill="#270e33")
            guide.text((31,30),"DEMO PLATE",fill="white")
            pixels=clean.copy()
            masks=[Image.new("L",pixels.size) for _ in range(2)]
            subjects=[]
            for layer in range(2 if shot==2 else 1):
                x,y=(width*.61,297) if layer==0 else (width*.28,230)
                scale=1 if layer==0 else .69
                j={i:(x+a*scale,y+(b+(math.sin(local*.31)*9 if i in (15,16) else 0))*scale) for i,(a,b) in POINTS.items()}
                for d,color in ((ImageDraw.Draw(pixels),"#f1b66c" if not layer else "#84bdb2"),(ImageDraw.Draw(masks[layer]),255)):
                    for a,b in BONES: d.line((j[a],j[b]),fill=color,width=round(22*scale))
                    cx,cy=j[0]; r=21*scale
                    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=color)
                    d.line((j[0],(x,y-108*scale)),fill=color,width=round(20*scale))
                    d.polygon([j[11],j[12],j[24],j[23]],fill=color)
                subjects.append([[round(a*4),round(b*4),100] for a,b in j.values()])
            tile=((frame%GRID)*TW,(frame//GRID)*TH)
            mask_atlas.paste(Image.merge("RGB",(*masks,Image.new("L",pixels.size))).resize((TW,TH)),tile)
            fill_atlas.paste(clean.resize((TW,TH)),tile)
            poses.append([width,subjects,1])
            image=av.VideoFrame.from_ndarray(np.asarray(pixels)[:,:width].copy(),format="rgb24")
            image.pts=frame
            image.time_base=Fraction(1,30)
            packets.extend(encoder.encode(image.reformat(format="yuv420p")))
        packets.extend(encoder.encode())
    with TemporaryDirectory() as scratch:
        probe=Path(scratch)/"header.h264"
        probe.write_bytes(b"".join(bytes(p) for p in packets[:3]))
        with av.open(str(probe),format="h264") as original,av.open(str(out/"video.mp4"),"w",options={"movflags":"+faststart"}) as movie:
            stream=movie.add_stream_from_template(original.streams.video[0])
            stream.codec_context.codec_tag="avc3"
            stream.time_base=Fraction(1,30)
            for i,packet in enumerate(packets):
                packet.stream=stream
                packet.pts=packet.dts=i
                packet.duration=1
                packet.time_base=Fraction(1,30)
                movie.mux(packet)
    mask_atlas.save(assets/"mask.png")
    fill_atlas.save(assets/"fill.png")
    meta={"fps":30,"height":HEIGHT,"tile":[TW,TH],"pixelScale":SCALE,"grid":GRID,
          "shots":[[0,16],[16,32],[32,48]],"protected":[[18,16,119,59]]*3,
          "reflection":[[0,0,WIDE,HEIGHT]]*3,"pages":[["mask.png","fill.png"]],
          "landmarks":list(POINTS),"frames":poses}
    (assets/"timeline.json").write_text(json.dumps(meta)+"\n")
    with av.open(str(out/"video.mp4")) as movie:
        frames=[(f.width,round(float(f.time)*30)) for f in movie.decode(video=0)]
    assert frames==[(row[0],i) for i,row in enumerate(poses)]


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    build(parser.parse_args().output)
