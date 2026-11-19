"""Lay out identically framed studio renders for comparison across varieties."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

VIEWS = ("three-quarter","overhead")
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("version",type=Path)
parser.add_argument("--serif-font",default="DejaVuSerif.ttf")
parser.add_argument("--sans-font",default="DejaVuSans.ttf")
args=parser.parse_args()
root=args.version.resolve()
catalog=json.loads((root/"review"/"catalog.json").read_text())
variants=catalog["variants"]
width,height=1490,218+414*len(variants)
sheet=Image.new("RGB",(width,height),"#111f20")
draw=ImageDraw.Draw(sheet)
heading=ImageFont.truetype(args.serif_font,64)
subheading=ImageFont.truetype(args.serif_font,32)
body=ImageFont.truetype(args.sans_font,21)
draw.text((36,24),catalog["title"],font=heading,fill="#f1ede1")
draw.text((38,104),"Material variants at the same scale",font=body,fill="#acbeb5")
for x,label in [(36,"Three-quarter"),(755,"Overhead")]:
    draw.text((x,159),label,font=body,fill="#acbeb5")
for i,entry in enumerate(variants):
    slug,name=entry["slug"],entry["label"]
    y=196+i*414
    draw.line((36,y,1454,y),fill="#2b4340",width=2)
    draw.text((36,y+13),name,font=subheading,fill="#f4eee0")

    for left,view in zip((36,755),VIEWS):
        path=root/"variants"/slug/"preview"/(view+".png")
        source=Image.open(path).convert("RGB")
        preview=ImageOps.fit(source,(699,338),getattr(Image,"Resampling",Image).LANCZOS)
        sheet.paste(preview,(left,y+60))
out=root/"preview"/"varieties.png"
out.parent.mkdir(exist_ok=True)
sheet.save(out,optimize=True)
