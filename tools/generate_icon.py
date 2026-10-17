#!/usr/bin/env python
"""Generate assets/icon.png and assets/icon.ico using only the standard library.

The icon is rasterised with supersampling from the same shape vocabulary as
Bubu himself, then wrapped in PNG/ICO containers written by hand. Run:

    python tools/generate_icon.py
"""

from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "assets"

SS = 4  # supersampling factor for the 256px master render
MASTER = 256
ICO_SIZES = (256, 128, 64, 48, 32, 24, 16)

FUR = (185, 141, 98)
CREAM = (247, 233, 210)
INNER = (229, 169, 155)
BLUSH = (239, 155, 166)
EYE = (51, 36, 26)
NOSE = (92, 66, 48)
WHITE = (255, 255, 255)


def _in_ellipse(x: float, y: float, cx: float, cy: float, rx: float, ry: float) -> bool:
    dx = (x - cx) / rx
    dy = (y - cy) / ry
    return dx * dx + dy * dy <= 1.0


def sample(x: float, y: float):
    """Colour at unit coordinates, painter's order (last match wins)."""
    color = None

    def put(hit: bool, c) -> None:
        nonlocal color
        if hit:
            color = c

    # ears, head (fur), then details
    put(_in_ellipse(x, y, 0.25, 0.215, 0.155, 0.145), FUR)
    put(_in_ellipse(x, y, 0.75, 0.215, 0.155, 0.145), FUR)
    put(_in_ellipse(x, y, 0.5, 0.55, 0.385, 0.365), FUR)
    put(_in_ellipse(x, y, 0.25, 0.225, 0.075, 0.068), INNER)
    put(_in_ellipse(x, y, 0.75, 0.225, 0.075, 0.068), INNER)
    put(_in_ellipse(x, y, 0.235, 0.655, 0.075, 0.05), BLUSH)
    put(_in_ellipse(x, y, 0.765, 0.655, 0.075, 0.05), BLUSH)
    put(_in_ellipse(x, y, 0.5, 0.695, 0.2, 0.145), CREAM)
    put(_in_ellipse(x, y, 0.375, 0.485, 0.055, 0.062), EYE)
    put(_in_ellipse(x, y, 0.625, 0.485, 0.055, 0.062), EYE)
    put(_in_ellipse(x, y, 0.360, 0.468, 0.017, 0.017), WHITE)
    put(_in_ellipse(x, y, 0.610, 0.468, 0.017, 0.017), WHITE)
    put(_in_ellipse(x, y, 0.5, 0.632, 0.062, 0.046), NOSE)
    # smile: lower arc of an annulus beneath the nose
    dx, dy = x - 0.5, y - 0.615
    dist = math.hypot(dx, dy)
    if y > 0.645 and 0.072 <= dist <= 0.104 and abs(dx) < 0.10:
        color = NOSE
    return color


def render(size: int, ss: int) -> list[bytearray]:
    rows: list[bytearray] = []
    total = ss * ss
    for py in range(size):
        row = bytearray()
        for px in range(size):
            r = g = b = a = 0
            hits = 0
            for sy in range(ss):
                yy = (py + (sy + 0.5) / ss) / size
                for sx in range(ss):
                    xx = (px + (sx + 0.5) / ss) / size
                    c = sample(xx, yy)
                    if c is None:
                        continue
                    r += c[0]
                    g += c[1]
                    b += c[2]
                    hits += 1
            if hits:
                row += bytes((r // hits, g // hits, b // hits, 255 * hits // total))
            else:
                row += b"\x00\x00\x00\x00"
        rows.append(row)
    return rows


def downsample(src_size: int, rows: list[bytearray], dst: int) -> list[bytearray]:
    factor = src_size / dst
    out: list[bytearray] = []
    for py in range(dst):
        y0 = int(py * factor)
        y1 = min(src_size, max(y0 + 1, int((py + 1) * factor + 1e-9)))
        row = bytearray()
        for px in range(dst):
            x0 = int(px * factor)
            x1 = min(src_size, max(x0 + 1, int((px + 1) * factor + 1e-9)))
            rs = gs = bs = as_ = cnt = 0
            for y in range(y0, y1):
                source = rows[y]
                for x in range(x0, x1):
                    i = x * 4
                    rs += source[i]
                    gs += source[i + 1]
                    bs += source[i + 2]
                    as_ += source[i + 3]
                    cnt += 1
            row += bytes((rs // cnt, gs // cnt, bs // cnt, as_ // cnt))
        out.append(row)
    return out


def png_bytes(size: int, rows: list[bytearray]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def write_ico(path: Path, images: list[tuple[int, bytes]]) -> None:
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    payloads = b""
    for size, data in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset
        )
        offset += len(data)
        payloads += data
    path.write_bytes(header + entries + payloads)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Rendering {MASTER}x{MASTER} icon (x{SS} supersampling)...")
    master = render(MASTER, SS)
    images = [(MASTER, png_bytes(MASTER, master))]
    for size in ICO_SIZES[1:]:
        images.append((size, png_bytes(size, downsample(MASTER, master, size))))

    (OUT_DIR / "icon.png").write_bytes(images[0][1])
    write_ico(OUT_DIR / "icon.ico", images)
    print(f"Wrote {OUT_DIR / 'icon.png'} and {OUT_DIR / 'icon.ico'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
