"""Tiny dependency-free PNG encoder — enough to send the being's body as an image."""
from __future__ import annotations
import struct
import zlib


def _chunk(typ: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + typ + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))


def encode_rgb(pixels, w: int, h: int) -> bytes:
    raw = bytearray()
    for y in range(h):
        raw.append(0)                       # filter type 0
        for x in range(w):
            r, g, b = pixels[y * w + x]
            raw += bytes((r & 255, g & 255, b & 255))
    comp = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + _chunk(b"IDAT", comp) + _chunk(b"IEND", b""))


def encode_scaled(cells, w: int, h: int, scale: int = 20) -> bytes:
    """cells: row-major list of [r,g,b]; upscales each cell to scale x scale."""
    W, H = w * scale, h * scale
    px = [(0, 0, 0)] * (W * H)
    for y in range(H):
        sy = (y // scale) * w
        for x in range(W):
            c = cells[sy + x // scale]
            px[y * W + x] = (int(c[0]), int(c[1]), int(c[2]))
    return encode_rgb(px, W, H)
