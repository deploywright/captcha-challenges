"""Independent checks of the existing catalog's pixel measurement contract.

Ponzo lengths use documented endpoint spans (one-pixel raster tolerance).
Muller-Lyer fins overlap the shaft endpoints, so only the documented geometry
and continuous shaft interior can be verified independently of fin segmentation.
Circle diameters use color runs through the documented centers. Mortar rows use
their documented y coordinates. Provenance is checked against the existing catalog;
this does not establish authorship or licensing beyond those supplied records.
"""
from __future__ import annotations

import math
import numpy as np
from PIL import Image


def verify_catalog_measurements(image: Image.Image, subtype: str, meta: dict) -> list[str]:
    errors: list[str] = []
    pixels = np.asarray(image.convert("RGB"))
    h, w = pixels.shape[:2]
    values = meta.get("measured_values", {})

    def run(cx: int, cy: int) -> tuple[int, int]:
        if not (0 <= cx < w and 0 <= cy < h):
            raise ValueError("Measurement point outside image")
        mask = np.all(pixels[cy] == pixels[cy, cx], axis=1)
        left = right = cx
        while left > 0 and mask[left-1]:
            left -= 1
        while right+1 < w and mask[right+1]:
            right += 1
        return left, right

    try:
        if subtype in {"muller-lyer", "ponzo"}:
            prefix = "line" if subtype == "muller-lyer" else "bar"
            lengths = []
            for label in ("a", "b"):
                x1,y1,x2,y2 = values[f"{prefix}_{label}_span"]
                if not (0 <= x1 < x2 < w and 0 <= y1 == y2 < h):
                    raise ValueError("Invalid horizontal endpoint span")
                left,right = run((x1+x2)//2, y1)
                if subtype == "muller-lyer":
                    if not (x1-8 <= left <= x1 and x2 <= right <= x2+8):
                        errors.append(f"{prefix} {label} shaft interior differs from raster")
                elif abs(left-x1) > 1 or abs(right-x2) > 1:
                    errors.append(f"{prefix} {label} raster endpoints differ from documented span")
                length = math.hypot(x2-x1,y2-y1)
                if length != values[f"{prefix}_{label}_length"]:
                    errors.append(f"{prefix} {label} documented length differs from endpoints")
                lengths.append(length if subtype == "muller-lyer" else right-left)
            if abs(lengths[0]-lengths[1]) > 1:
                errors.append("Horizontal lengths differ")
        elif subtype == "ebbinghaus":
            diameters = []
            for label in ("a", "b"):
                cx,cy = values[f"circle_{label}_center"]
                left,right = run(cx,cy)
                diameter = right-left
                if abs(diameter-values[f"circle_{label}_diameter"]) > 1:
                    errors.append(f"Circle {label} diameter differs from raster")
                diameters.append(diameter)
            if abs(diameters[0]-diameters[1]) > 1:
                errors.append("Circle diameters differ")
        elif subtype == "simultaneous-contrast":
            means = []
            for label in ("a", "b"):
                x1,y1,x2,y2 = meta["regions"][f"square_{label}_interior"]
                if not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
                    raise ValueError("Invalid shade sampling box")
                patch = pixels[y1:y2,x1:x2]
                mean = patch.mean(axis=(0,1))
                if not np.allclose(mean, values[f"square_{label}_rgb"], atol=1):
                    errors.append(f"Square {label} RGB differs from raster")
                means.append(mean)
            if not np.allclose(means[0],means[1],atol=1):
                errors.append("Patch shades differ")
        elif subtype == "cafe-wall":
            if values["slope"] != 0 or not values["is_strictly_parallel"]:
                errors.append("Catalog does not describe parallel horizontal lines")
            for y in values["mortar_y_positions"]:
                if not 0 <= y < h:
                    raise ValueError("Invalid mortar row")
                row = pixels[y, 2:w-2]
                if np.any(row.max(axis=0)-row.min(axis=0) > 1):
                    errors.append(f"Mortar row {y} is not a continuous horizontal line")
        else:
            errors.append(f"Unsupported measurement subtype: {subtype}")
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        errors.append(f"Invalid measurement metadata: {exc}")
    return errors
