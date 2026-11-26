"""Reusable reportlab scaffolding for composing assembly install-guide PDFs.

The caller imports these helpers and supplies project-specific content
(images, hardware lists, steps, tile maps).  This module handles page
layout, image fitting, numbered steps, bullet lists, tinted boxes, and
consistent typography.

Requires: reportlab  (`pip install reportlab`)
"""
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ---------------------------------------------------------------------------
# Default color palette (project scripts can override)
# ---------------------------------------------------------------------------
DARK = HexColor('#1a1a1a')
MID = HexColor('#555555')
ACCENT = HexColor('#c45a2c')
GOLD = HexColor('#d4a520')
BLUE = HexColor('#4a8abf')
LIGHT_BG = HexColor('#f5f4f0')
BOX_BG = HexColor('#eae8e2')
WARN_BG = HexColor('#fff3e0')

# Page geometry
W, H = letter
MARGIN = 0.6 * inch
CW = W - 2 * MARGIN


# ---------------------------------------------------------------------------
# Text primitives
# ---------------------------------------------------------------------------

def draw_header(c, y, text, size=16, color=None):
    if color is None:
        color = DARK
    c.setFont('Helvetica-Bold', size)
    c.setFillColor(color)
    c.drawString(MARGIN, y, text)
    return y - size - 4


def draw_text(c, y, text, size=10, color=None, font='Helvetica',
              indent=0, max_width=None):
    if color is None:
        color = DARK
    c.setFont(font, size)
    c.setFillColor(color)
    if max_width is None:
        max_width = CW - indent

    words = text.split()
    lines, current = [], ''
    for w in words:
        test = f'{current} {w}'.strip()
        if c.stringWidth(test, font, size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)

    for line in lines:
        c.drawString(MARGIN + indent, y, line)
        y -= size + 3
    return y


def draw_bullet(c, y, text, size=10, indent=15):
    c.setFont('Helvetica', size)
    c.setFillColor(DARK)
    c.drawString(MARGIN + indent - 10, y, '•')
    return draw_text(c, y, text, size=size, indent=indent)


def draw_step(c, y, num, text, size=10, accent=None):
    if accent is None:
        accent = ACCENT
    cx = MARGIN + 8
    cy = y + 3
    c.setFillColor(accent)
    c.circle(cx, cy, 8, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 9)
    c.drawCentredString(cx, cy - 3, str(num))
    return draw_text(c, y, text, size=size, indent=24)


# ---------------------------------------------------------------------------
# Image placement
# ---------------------------------------------------------------------------

def draw_image(c, y, img_path, max_w=None, max_h=None, caption=None):
    if max_w is None:
        max_w = CW
    if max_h is None:
        max_h = 3.5 * inch

    img = ImageReader(img_path)
    iw, ih = img.getSize()
    aspect = iw / ih

    w = max_w
    h = w / aspect
    if h > max_h:
        h = max_h
        w = h * aspect
    if w > max_w:
        w = max_w
        h = w / aspect

    x = MARGIN + (CW - w) / 2
    img_y = y - h

    c.setFillColor(LIGHT_BG)
    c.roundRect(x - 4, img_y - 4, w + 8, h + 8, 4, fill=1, stroke=0)
    c.drawImage(img_path, x, img_y, w, h, preserveAspectRatio=True)

    if caption:
        c.setFont('Helvetica-Oblique', 8)
        c.setFillColor(MID)
        c.drawCentredString(W / 2, img_y - 14, caption)
        return img_y - 22

    return img_y - 8


# ---------------------------------------------------------------------------
# Tinted boxes
# ---------------------------------------------------------------------------

def draw_box(c, y, height, bg_color=None):
    if bg_color is None:
        bg_color = BOX_BG
    c.setFillColor(bg_color)
    c.roundRect(MARGIN, y - height, CW, height, 6, fill=1, stroke=0)
    return y


def draw_warning_box(c, y, title, lines, height=55):
    draw_box(c, y, height, bg_color=WARN_BG)
    c.setFillColor(ACCENT)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(MARGIN + 10, y - 15, title)
    c.setFont('Helvetica', 9)
    c.setFillColor(DARK)
    ly = y - 30
    for line in lines:
        c.drawString(MARGIN + 10, ly, line)
        ly -= 12
    return y - height - 5


# ---------------------------------------------------------------------------
# Page management
# ---------------------------------------------------------------------------

def new_page(c, running_title=None, page_label=None):
    c.showPage()
    if running_title:
        c.setFont('Helvetica', 8)
        c.setFillColor(MID)
        c.drawString(MARGIN, H - MARGIN / 2, running_title)
        if page_label:
            c.drawRightString(W - MARGIN, H - MARGIN / 2, page_label)
    return H - MARGIN - 10


def create_canvas(output_path, title=None, author=None):
    c = canvas.Canvas(output_path, pagesize=letter)
    if title:
        c.setTitle(title)
    if author:
        c.setAuthor(author)
    return c
