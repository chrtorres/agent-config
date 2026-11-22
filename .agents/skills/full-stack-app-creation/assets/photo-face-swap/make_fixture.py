"""Draw two fictional faces for a portable test."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def portrait(path, skin, hair, backdrop, pupil, smile):
    image = Image.new("RGB", (480, 520), backdrop)
    draw = ImageDraw.Draw(image)
    draw.ellipse((60, 420, 420, 700), fill=(111, 137, 149))
    draw.rectangle((197, 382, 283, 473), fill=skin)
    draw.ellipse((101, 43, 379, 385), fill=hair)
    draw.ellipse((107, 234, 148, 310), fill=skin)
    draw.ellipse((332, 234, 373, 310), fill=skin)
    draw.ellipse((126, 81, 354, 425), fill=skin)
    # Draw facial planes on a separate layer so shading has no hard edges.
    shade = Image.new("RGBA", image.size)
    shadow = ImageDraw.Draw(shade)
    shadow.ellipse((130, 170, 183, 342), fill=(87, 51, 42, 75))
    shadow.ellipse((298, 162, 353, 342), fill=(87, 51, 42, 88))
    shadow.ellipse((166, 116, 305, 210), fill=(255, 239, 221, 110))
    shadow.ellipse((165, 286, 203, 352), fill=(240, 125, 111, 95))
    shadow.ellipse((277, 286, 315, 352), fill=(240, 125, 111, 95))
    shadow.ellipse((212, 236, 251, 311), fill=(132, 72, 64, 80))
    shade = shade.filter(ImageFilter.GaussianBlur(13))
    image.paste(shade, mask=shade.getchannel("A"))
    draw = ImageDraw.Draw(image)
    for x in (187, 293):
        draw.arc((x - 33, 211, x + 32, 240), 195, 340, fill=hair, width=6)
        draw.ellipse((x - 27, 244, x + 27, 264), fill=(77, 51, 48))
        draw.ellipse((x - 23, 248, x + 23, 263), fill=(236, 223, 210))
        draw.ellipse((x - 8, 245, x + 8, 263), fill=pupil)
        draw.ellipse((x - 4, 248, x + 4, 259), fill=(39, 32, 30))
        draw.ellipse((x + 1, 247, x + 4, 250), fill=(246, 238, 226))
    draw.arc((216, 270, 264, 317), 12, 168, fill=(127, 74, 63), width=4)
    draw.ellipse((223, 311, 230, 315), fill=(95, 57, 52))
    draw.ellipse((249, 311, 256, 315), fill=(95, 57, 52))
    if smile:
        draw.ellipse((198, 342, 282, 374), fill=(153, 77, 71))
        draw.ellipse((207, 349, 273, 362), fill=(246, 232, 220))
    else:
        draw.ellipse((203, 344, 277, 361), fill=(160, 89, 82))
        draw.line((208, 352, 272, 352), fill=(108, 56, 50), width=3)
    image.filter(ImageFilter.GaussianBlur(1.1)).save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    portrait(args.directory / "source.png", (190, 136, 106), (58, 38, 36),
             (46, 92, 109), (63, 80, 52), True)
    portrait(args.directory / "target.png", (224, 171, 136), (40, 34, 38),
             (116, 104, 124), (78, 104, 126), False)


if __name__ == "__main__":
    main()
