"""Checks applied before parsing, caching, logging, or using public JSON."""

import re
from typing import Any

from .errors import PublicDataLeakError

# Normalize punctuation/case so nested snake_case and camelCase leaks also fail closed.
_FORBIDDEN = {
    "answer",
    "answers",
    "correctanswer",
    "correctselection",
    "privateanswer",
    "routing",
    "connections",
    "solutionpath",
    "targetclass",
    "sourceimageid",
    "sourcepath",
    "boundingbox",
    "boundingboxes",
    "bbox",
    "bboxes",
    "crop",
    "cropmetadata",
    "cropbox",
    "groundtruth",
    "labels",
    "annotations",
    "generator",
    "generationmetadata",
    "privatemetadata",
    "privatemanifest",
    "routingmetadata",
}


def assert_public_json(value: Any) -> None:
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            for key, child in current.items():
                normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
                if normalized in _FORBIDDEN:
                    raise PublicDataLeakError()
                pending.append(child)
        elif isinstance(current, list):
            pending.extend(current)
