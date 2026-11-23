"""Draw a labelled pixel grid over an enlarged crop of a reference photo, for reading landmark positions.

    python3 photo_measure_grid.py <photo> <out.jpg> --crop x0 y0 x1 y1 [--zoom 2] [--step 20]

Grid labels are in ORIGINAL photo pixels, so picks can be written straight into a landmark file. Express
measurements as ratios to a span in the same plane (for a face: head width at the eyes), not as absolute sizes,
and record the pick uncertainty (typically +/- a few original pixels).
"""
import argparse, sys
from PIL import Image, ImageDraw


def grid(photo, crop, zoom=2.0, step=20):
    x0, y0, x1, y1 = crop
    im = Image.open(photo).convert('RGB').crop((x0, y0, x1, y1))
    im = im.resize((int((x1 - x0) * zoom), int((y1 - y0) * zoom)))
    d = ImageDraw.Draw(im)
    for y in range(y0 - y0 % step + step, y1, step):
        py = (y - y0) * zoom; d.line([(0, py), (im.width, py)], fill=(255, 0, 0)); d.text((2, py + 1), str(y), fill=(255, 255, 0))
    for x in range(x0 - x0 % step + step, x1, step):
        px = (x - x0) * zoom; d.line([(px, 0), (px, 8)], fill=(0, 255, 0)); d.text((px + 1, 10), str(x), fill=(0, 255, 0))
    return im


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('photo'); ap.add_argument('out')
    ap.add_argument('--crop', type=int, nargs=4, required=True); ap.add_argument('--zoom', type=float, default=2.0)
    ap.add_argument('--step', type=int, default=20)
    a = ap.parse_args(argv)
    grid(a.photo, a.crop, a.zoom, a.step).save(a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
