"""Hair and facial-feature color controls. Mirrors app/colors.mjs.

A dye keeps each pixel's lightness (with a partial lift toward the chosen
color's own lightness) and takes the chosen hue and saturation, the way a
"color" blend mode works, so texture and shading survive the change.
"""
import re

import cv2
import numpy as np

TARGETS = ("hair", "lips", "eyes", "brows")
LUMA = np.float32([.2126, .7152, .0722])
# How far a dyed pixel's lightness moves toward the dye's own lightness.
# Hair lifts further so dark hair can take a lighter color.
LIFT = {"hair": .6, "lips": .35, "eyes": .35, "brows": .35}


def hex_color(value):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return None
    number = int(value[1:], 16)
    return np.float32([(number >> 16)/255, ((number >> 8) & 255)/255, (number & 255)/255])


def valid_colors(colors):
    if colors is None:
        return {}
    if not isinstance(colors, dict):
        raise ValueError("Colors must map targets to [color, strength]")
    result = {}
    for key, entry in colors.items():
        if (key not in TARGETS or not isinstance(entry, list) or len(entry) != 2 or hex_color(entry[0]) is None
                or type(entry[1]) not in (int, float) or not 0 <= entry[1] <= 100):
            raise ValueError(f"Invalid color for {key}")
        if entry[1] > 0:
            result[key] = (hex_color(entry[0]), entry[1]/100)
    return result


def set_luminosity(color, luminosity):
    """W3C compositing SetLum with ClipColor, vectorized over pixels."""
    color = color+(luminosity-color @ LUMA)[..., None]
    lum = (color @ LUMA)[..., None]
    low, high = color.min(axis=-1, keepdims=True), color.max(axis=-1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        color = np.where(low < 0, lum+(color-lum)*lum/np.maximum(lum-low, 1e-6), color)
        color = np.where(high > 1, lum+(color-lum)*(1-lum)/np.maximum(high-lum, 1e-6), color)
    return np.clip(color, 0, 1)


def dye(color, target, strength, mask, lift=.35):
    """color: float RGB 0..1 (H,W,3); mask: (H,W) weight 0..1."""
    lum = color @ LUMA
    lifted = np.clip(lum+(float(target @ LUMA)-lum)*lift, 0, 1)
    dyed = set_luminosity(np.broadcast_to(target, color.shape).astype(np.float32), lifted)
    weight = (mask*strength)[..., None]
    return color+(dyed-color)*weight


def feature_masks(areas, size):
    """Lips, irises and brows weights (H,W) in source pixels, or None."""
    if not areas:
        return None
    width, height = size
    polygon = lambda points: np.rint(np.asarray(points, np.float32)).astype(np.int32)
    lips = np.zeros((height, width), np.float32)
    cv2.fillPoly(lips, [polygon(areas["lips"])], 1)
    cv2.fillPoly(lips, [polygon(areas["mouth"])], 0)
    irises = np.zeros_like(lips)
    for index, eye in enumerate(areas.get("eyes", [])):
        iris = (areas.get("irises") or [None, None])[index]
        if iris is None:
            continue
        opening, disc = np.zeros_like(lips), np.zeros_like(lips)
        cv2.fillPoly(opening, [polygon(eye)], 1)
        cv2.circle(disc, (round(iris[0]), round(iris[1])), max(1, round(iris[2])), 1, -1)
        irises = np.maximum(irises, opening*disc)
    brows = np.zeros_like(lips)
    for brow in areas.get("brows", []):
        cv2.fillPoly(brows, [polygon(brow)], 1)
    return [cv2.GaussianBlur(mask, (0, 0), .8) for mask in (lips, irises, brows)]


def apply_colors(rgb, colors, hair=None, areas=None):
    """Dye hair (from the segmentation weight) and facial features in one frame."""
    if not colors:
        return rgb
    color = rgb.astype(np.float32)/255
    if "hair" in colors and hair is not None:
        color = dye(color, *colors["hair"], hair, LIFT["hair"])
    masks = feature_masks(areas, (rgb.shape[1], rgb.shape[0])) if areas and set(colors) & {"lips", "eyes", "brows"} else None
    if masks is not None:
        for key, mask in zip(("lips", "eyes", "brows"), masks):
            if key in colors:
                color = dye(color, *colors[key], mask, LIFT[key])
    return np.rint(np.clip(color, 0, 1)*255).astype(np.uint8)
