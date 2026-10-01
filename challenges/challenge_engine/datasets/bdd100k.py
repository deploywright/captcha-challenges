"""Shared BDD100K dataset adapter, annotation analyzer, and difficulty filter for Levels 1, 2A, and 3B.

CRITICAL DATA-SPLIT RULE:
- BDD100K official `train` split is RESERVED EXCLUSIVELY for future AI solver training.
- BDD100K official `val` split is RESERVED EXCLUSIVELY for challenge generation (held-out benchmark).
- This adapter enforces `source_split == "val"` and rejects any `train` split paths or annotations.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Sequence

from PIL import Image

from challenge_engine.core.config import PROJECT_ROOT
from challenge_engine.core.random import DeterministicRNG

DEFAULT_BDD100K_ROOT = PROJECT_ROOT / "data" / "bdd100k"
BENCHMARK_SOURCE_DATASET = "BDD100K"
BENCHMARK_SOURCE_SPLIT = "val"
BENCHMARK_PROJECT_ROLE = "held_out_benchmark"

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_FORBIDDEN_SPLIT_DIRS = {"train", "traina", "trainb", "test", "testa", "testb", "10k"}

# Canonical category mapping across BDD100K Det20 and BDD100K 100k label conventions
_CATEGORY_ALIASES: dict[str, str] = {
    "motorcycle": "motorcycle",
    "motor": "motorcycle",
    "bicycle": "bicycle",
    "bike": "bicycle",
    "bus": "bus",
    "car": "car",
    "truck": "truck",
    "traffic light": "traffic light",
    "traffic-light": "traffic light",
    "traffic_light": "traffic light",
    "traffic sign": "traffic sign",
    "traffic-sign": "traffic sign",
    "traffic_sign": "traffic sign",
    "person": "person",
    "pedestrian": "pedestrian",
    "rider": "rider",
    "train": "train",
    "other vehicle": "other vehicle",
    "other person": "other person",
    "trailer": "trailer",
}

CONFUSABLE_DISTRACTORS: dict[str, set[str]] = {
    "motorcycle": {"bicycle", "rider"},
    "bicycle": {"motorcycle", "rider"},
    "bus": {"truck", "train", "car"},
    "car": {"truck", "bus"},
    "traffic light": {"traffic sign"},
}


def normalize_bdd100k_category(raw_category: str) -> str:
    """Normalize BDD100K category names (e.g. 'motor' -> 'motorcycle', 'traffic-light' -> 'traffic light')."""
    cleaned = raw_category.strip().lower()
    return _CATEGORY_ALIASES.get(cleaned, cleaned)


def extract_sequence_id(filename: str) -> str | None:
    """Extract the driving video/sequence prefix from a BDD100K filename (e.g. 'b1c66a42-6f7d68ca.jpg' -> 'b1c66a42')."""
    stem = Path(filename).stem
    if "-" in stem:
        prefix, suffix = stem.split("-", 1)
        if len(prefix) == 8 and len(suffix) == 8:
            return prefix
    return None


class BDD100KNotFoundError(FileNotFoundError):
    """Raised when the local BDD100K dataset directory, images, or annotations are missing."""


class BDD100KDataSplitError(ValueError):
    """Raised when an attempt is made to use the BDD100K `train` split for benchmark challenge generation."""


@dataclass
class BDD100KObjectAnnotation:
    """Single 2D bounding box object annotation inside a BDD100K frame."""

    category: str
    raw_category: str
    box2d: tuple[float, float, float, float]
    occluded: bool = False
    truncated: bool = False
    traffic_light_color: str = "none"
    frame_width: int = 1280
    frame_height: int = 720

    @property
    def width(self) -> float:
        return max(0.0, self.box2d[2] - self.box2d[0])

    @property
    def height(self) -> float:
        return max(0.0, self.box2d[3] - self.box2d[1])

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def area_ratio(self) -> float:
        denom = float(max(1, self.frame_width * self.frame_height))
        return self.area / denom

    @property
    def min_dimension(self) -> float:
        return min(self.width, self.height)

    @property
    def aspect_ratio(self) -> float:
        return self.width / max(1.0, self.height)


@dataclass
class BDD100KFrameRecord:
    """Indexed BDD100K validation frame with scene attributes, object annotations, and provenance."""

    name: str
    image_path: Path
    source_path: str = ""
    source_split: str = BENCHMARK_SOURCE_SPLIT
    source_dataset: str = BENCHMARK_SOURCE_DATASET
    project_role: str = BENCHMARK_PROJECT_ROLE
    sequence_id: str | None = None
    weather: str = "undefined"
    scene: str = "undefined"
    timeofday: str = "undefined"
    frame_width: int = 1280
    frame_height: int = 720
    objects: list[BDD100KObjectAnnotation] = field(default_factory=list)

    @property
    def categories(self) -> set[str]:
        return {obj.category for obj in self.objects}

    @property
    def raw_categories(self) -> set[str]:
        return {obj.raw_category for obj in self.objects}

    def has_category(self, target: str) -> bool:
        norm = normalize_bdd100k_category(target)
        return norm in self.categories

    def objects_for_category(self, target: str) -> list[BDD100KObjectAnnotation]:
        norm = normalize_bdd100k_category(target)
        return [obj for obj in self.objects if obj.category == norm]

    def evaluate_for_target(
        self,
        target: str,
        min_easy_area_ratio: float = 0.012,
        min_easy_dimension: float = 36.0,
    ) -> dict[str, Any]:
        """Analyze bounding boxes and scene attributes for `target` to determine easy/hard suitability."""
        norm_target = normalize_bdd100k_category(target)
        target_objs = self.objects_for_category(norm_target)
        total_objs = len(self.objects)
        confusable_set = CONFUSABLE_DISTRACTORS.get(norm_target, set())
        has_confusable = bool(self.categories & confusable_set)

        difficulty_tags: list[str] = []
        if self.timeofday in {"night", "dawn/dusk"}:
            difficulty_tags.append("night" if self.timeofday == "night" else "low-light")
            if "low-light" not in difficulty_tags:
                difficulty_tags.append("low-light")
        if self.weather in {"rainy", "snowy", "foggy"}:
            difficulty_tags.append("rain" if self.weather == "rainy" else self.weather)
        if total_objs >= 10:
            difficulty_tags.append("dense-traffic")
        if has_confusable:
            difficulty_tags.append("confusable-object")

        if not target_objs:
            is_ambiguous_negative = (
                norm_target in {"motorcycle", "bicycle"}
                and "rider" in self.categories
                and "motorcycle" not in self.categories
                and "bicycle" not in self.categories
            )
            is_clear_negative = (
                not is_ambiguous_negative
                and self.timeofday not in {"night", "dawn/dusk"}
                and self.weather not in {"rainy", "snowy", "foggy"}
                and not has_confusable
            )
            hard_neg_score = (
                (3 if has_confusable else 0)
                + (2 if total_objs >= 8 else 0)
                + (2 if self.timeofday in {"night", "dawn/dusk"} else 0)
                + (2 if self.weather in {"rainy", "snowy", "foggy"} else 0)
            )
            return {
                "is_positive": False,
                "is_easy_positive": False,
                "is_hard_positive": False,
                "is_microscopic_positive": False,
                "is_borderline_small_positive": False,
                "is_ambiguous_negative": is_ambiguous_negative,
                "is_clear_negative": is_clear_negative,
                "easy_score": 1.0 if is_clear_negative else 0.2,
                "hard_score": float(hard_neg_score),
                "max_target_area_ratio": 0.0,
                "max_target_min_dimension": 0.0,
                "difficulty_tags": sorted(set(difficulty_tags)),
            }

        best_area_ratio = max(o.area_ratio for o in target_objs)
        best_min_dim = max(o.min_dimension for o in target_objs)

        is_microscopic = best_area_ratio < 0.0010 or best_min_dim < 28.0
        is_borderline_small = (not is_microscopic) and (
            best_area_ratio < 0.0025 or best_min_dim < 36.0
        )

        any_unoccluded_large = any(
            (not o.occluded)
            and (not o.truncated)
            and o.area_ratio >= min_easy_area_ratio
            and o.min_dimension >= min_easy_dimension
            for o in target_objs
        )
        any_foreground_clear = any(
            (not o.truncated)
            and o.area_ratio >= max(0.015, min_easy_area_ratio * 1.2)
            and o.min_dimension >= 85.0
            for o in target_objs
        )

        if any(o.occluded for o in target_objs):
            difficulty_tags.append("occluded")
        if any(o.truncated for o in target_objs):
            difficulty_tags.append("truncated")
        if best_area_ratio < min_easy_area_ratio or best_min_dim < min_easy_dimension:
            difficulty_tags.append("small-object")
            if best_area_ratio < min_easy_area_ratio * 0.5:
                difficulty_tags.append("distant-object")
        if any(o.aspect_ratio > 2.4 or o.aspect_ratio < 0.42 for o in target_objs):
            difficulty_tags.append("unusual-angle")

        is_easy_positive = (
            (not is_microscopic)
            and (any_unoccluded_large or any_foreground_clear)
            and self.timeofday not in {"night", "dawn/dusk"}
            and self.weather not in {"rainy", "snowy", "foggy"}
        )

        hard_tags_present = [
            t
            for t in difficulty_tags
            if t
            in {
                "small-object",
                "distant-object",
                "occluded",
                "truncated",
                "night",
                "low-light",
                "rain",
                "dense-traffic",
                "unusual-angle",
                "confusable-object",
            }
        ]
        is_hard_positive = (
            (not is_microscopic)
            and ((not is_easy_positive) or len(hard_tags_present) >= 1)
        )

        easy_score = best_area_ratio * 100.0 + (2.0 if self.timeofday == "daytime" else 0.0)
        hard_score = float(
            len(set(hard_tags_present)) * 2.0 + (1.5 if not any_unoccluded_large else 0.0)
        )

        return {
            "is_positive": True,
            "is_easy_positive": is_easy_positive,
            "is_hard_positive": is_hard_positive,
            "is_microscopic_positive": is_microscopic,
            "is_borderline_small_positive": is_borderline_small,
            "is_ambiguous_negative": False,
            "is_clear_negative": False,
            "easy_score": easy_score,
            "hard_score": hard_score,
            "max_target_area_ratio": round(best_area_ratio, 6),
            "max_target_min_dimension": round(best_min_dim, 2),
            "difficulty_tags": sorted(set(difficulty_tags)),
        }


@dataclass
class BDD100KStatus:
    """Diagnostic status for the shared BDD100K validation benchmark dataset."""

    available: bool
    root_dir: Path
    source_split: str
    project_role: str
    image_dir: Path | None
    image_count: int
    annotated_frame_count: int
    annotation_files: list[Path]
    class_image_counts: dict[str, int]
    class_box_counts: dict[str, int]
    message: str


def resolve_bdd100k_root(custom_root: str | Path | None = None) -> Path:
    """Resolve the BDD100K root path from argument, BDD100K_ROOT env var, or default `data/bdd100k`."""
    if custom_root is not None:
        p = Path(custom_root)
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
    env_root = os.environ.get("BDD100K_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return DEFAULT_BDD100K_ROOT.resolve()


def _assert_not_train_path(path: Path, root_dir: Path) -> None:
    """Raise BDD100KDataSplitError if `path` is inside a `train` split directory or file."""
    try:
        rel_parts = [p.lower() for p in path.relative_to(root_dir).parts]
    except ValueError:
        rel_parts = [p.lower() for p in path.parts]

    for part in rel_parts:
        if part in {"train", "traina", "trainb"} or "det_train" in part or "bdd100k_labels_images_train" in part:
            raise BDD100KDataSplitError(
                f"Data leakage protection: path '{path}' belongs to the BDD100K 'train' split, "
                f"which is strictly reserved for future AI solver training."
            )


def _discover_val_images(root_dir: Path, split: str = "val") -> tuple[dict[str, Path], Path | None]:
    """Locate BDD100K validation split images under `root_dir` without scanning `train` or `test`."""
    norm_split = split.strip().lower()
    if norm_split != "val":
        raise BDD100KDataSplitError(
            f"Forbidden BDD100K split '{split}'. Challenge generation must use 'val' split only; "
            f"'train' is strictly reserved for future AI training."
        )

    image_map: dict[str, Path] = {}
    if not root_dir.exists():
        return image_map, None

    if root_dir.name.lower() in {"train", "traina", "trainb"} or "train" in [
        p.lower() for p in root_dir.parts[-3:]
    ]:
        raise BDD100KDataSplitError(
            f"Forbidden BDD100K root directory '{root_dir}': points to 'train' split."
        )

    explicit_val_dirs = [
        root_dir / "images" / "100k" / "val",
        root_dir / "bdd100k" / "images" / "100k" / "val",
        root_dir / "100k" / "val",
        root_dir / "images" / "val",
        root_dir / "bdd100k" / "images" / "val",
        root_dir / "val",
    ]
    for v_dir in explicit_val_dirs:
        if v_dir.exists() and v_dir.is_dir():
            with os.scandir(v_dir) as it:
                entries = sorted(it, key=lambda e: e.name)
                for entry in entries:
                    if entry.is_file():
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in _IMAGE_EXTENSIONS:
                            p = Path(entry.path)
                            stem = os.path.splitext(entry.name)[0]
                            image_map.setdefault(entry.name, p)
                            image_map.setdefault(stem, p)
            if image_map:
                return image_map, v_dir

    fallback_roots = [root_dir / "images", root_dir]
    for s_root in fallback_roots:
        if not s_root.exists() or not s_root.is_dir():
            continue
        for cur_root, dirnames, filenames in os.walk(s_root):
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d.lower() not in _FORBIDDEN_SPLIT_DIRS
                and d.lower() not in {"labels", "annotations", ".git", "__pycache__"}
            )
            for fname in sorted(filenames):
                ext = os.path.splitext(fname)[1].lower()
                if ext in _IMAGE_EXTENSIONS:
                    p = Path(cur_root) / fname
                    _assert_not_train_path(p, root_dir)
                    stem = os.path.splitext(fname)[0]
                    image_map.setdefault(fname, p)
                    image_map.setdefault(stem, p)
        if image_map:
            return image_map, s_root

    return image_map, None


def _discover_val_annotation_files(root_dir: Path, split: str = "val") -> list[Path]:
    """Locate BDD100K validation JSON / JSONL annotation files under `root_dir`."""
    if split.strip().lower() != "val":
        raise BDD100KDataSplitError(
            f"Forbidden BDD100K split '{split}'. Only 'val' annotations may be loaded."
        )
    if not root_dir.exists():
        return []

    candidates: list[Path] = []
    train_files_seen: list[Path] = []
    search_dirs = [
        root_dir / "labels",
        root_dir / "bdd100k" / "labels",
        root_dir / "annotations",
        root_dir,
    ]
    seen: set[Path] = set()
    for s_dir in search_dirs:
        if not s_dir.exists() or not s_dir.is_dir():
            continue
        for cur_root, dirnames, filenames in os.walk(s_dir):
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d.lower() not in {"images", "train", "test", "10k", "__pycache__"}
            )
            for fname in sorted(filenames):
                lower_name = fname.lower()
                if not (lower_name.endswith(".json") or lower_name.endswith(".jsonl")):
                    continue
                if lower_name == "benchmark_manifest.json":
                    continue
                p = (Path(cur_root) / fname).resolve()
                if p in seen:
                    continue
                seen.add(p)
                if "train" in lower_name:
                    train_files_seen.append(p)
                    continue
                candidates.append(p)
        if candidates:
            break

    if not candidates and train_files_seen:
        raise BDD100KDataSplitError(
            f"Refusing to load BDD100K 'train' annotation file(s) {[str(p) for p in train_files_seen]}. "
            f"Only 'val' annotations are permitted for challenge generation."
        )
    return candidates


_DATASET_CACHE: dict[tuple[str, str, float], "BDD100KDataset"] = {}


def load_bdd100k_dataset(
    root_dir: str | Path | None = None,
    split: str = "val",
    use_cache: bool = True,
) -> "BDD100KDataset":
    """Load (or retrieve from in-memory cache) the validated BDD100K `val` dataset."""
    resolved = resolve_bdd100k_root(root_dir)
    norm_split = split.strip().lower()
    if norm_split != "val":
        raise BDD100KDataSplitError(
            f"Forbidden BDD100K split '{split}'. Challenge generation must use 'val' split only."
        )
    if not use_cache:
        return BDD100KDataset(resolved, split=norm_split)

    ann_files = _discover_val_annotation_files(resolved, split=norm_split)
    mtime = max((p.stat().st_mtime for p in ann_files), default=0.0)
    cache_key = (str(resolved), norm_split, mtime)
    if cache_key not in _DATASET_CACHE:
        _DATASET_CACHE[cache_key] = BDD100KDataset(resolved, split=norm_split)
    return _DATASET_CACHE[cache_key]


def inspect_bdd100k_status(custom_root: str | Path | None = None) -> BDD100KStatus:
    """Check whether BDD100K `val` images and annotations are present without raising an exception."""
    root = resolve_bdd100k_root(custom_root)
    if not root.exists():
        return BDD100KStatus(
            available=False,
            root_dir=root,
            source_split=BENCHMARK_SOURCE_SPLIT,
            project_role=BENCHMARK_PROJECT_ROLE,
            image_dir=None,
            image_count=0,
            annotated_frame_count=0,
            annotation_files=[],
            class_image_counts={},
            class_box_counts={},
            message=(
                f"BDD100K directory does not exist at {root}. "
                f"Place BDD100K validation images under '{root / 'images' / '100k' / 'val'}' "
                f"and annotations under '{root / 'labels'}', or set BDD100K_ROOT / --bdd100k-root."
            ),
        )

    try:
        image_map, img_dir = _discover_val_images(root, split="val")
        unique_images = len(set(image_map.values()))
        ann_files = _discover_val_annotation_files(root, split="val")
    except Exception as exc:
        return BDD100KStatus(
            available=False,
            root_dir=root,
            source_split=BENCHMARK_SOURCE_SPLIT,
            project_role=BENCHMARK_PROJECT_ROLE,
            image_dir=None,
            image_count=0,
            annotated_frame_count=0,
            annotation_files=[],
            class_image_counts={},
            class_box_counts={},
            message=f"BDD100K validation split check failed at {root}: {exc}",
        )

    if unique_images == 0 or not ann_files:
        return BDD100KStatus(
            available=False,
            root_dir=root,
            source_split=BENCHMARK_SOURCE_SPLIT,
            project_role=BENCHMARK_PROJECT_ROLE,
            image_dir=img_dir,
            image_count=unique_images,
            annotated_frame_count=0,
            annotation_files=ann_files,
            class_image_counts={},
            class_box_counts={},
            message=(
                f"BDD100K validation dataset incomplete at {root} "
                f"(found {unique_images} val image files and {len(ann_files)} val annotation files). "
                f"Expected real BDD100K val images and label JSON files in '{root / 'labels'}'."
            ),
        )

    try:
        ds = load_bdd100k_dataset(root, split="val", use_cache=True)
        class_img_counts, class_box_counts = ds.class_statistics()
        motor_imgs = class_img_counts.get("motorcycle", 0)
        motor_boxes = class_box_counts.get("motorcycle", 0)
        return BDD100KStatus(
            available=True,
            root_dir=root,
            source_split=BENCHMARK_SOURCE_SPLIT,
            project_role=BENCHMARK_PROJECT_ROLE,
            image_dir=ds.image_dir,
            image_count=unique_images,
            annotated_frame_count=len(ds.frames),
            annotation_files=ann_files,
            class_image_counts=class_img_counts,
            class_box_counts=class_box_counts,
            message=(
                f"BDD100K READY (split='val', role='held_out_benchmark', "
                f"val_images={unique_images}, annotated_val_records={len(ds.frames)}, "
                f"motorcycle={motor_imgs} images / {motor_boxes} boxes, "
                f"labels={[p.name for p in ann_files]})."
            ),
        )
    except Exception as exc:
        return BDD100KStatus(
            available=False,
            root_dir=root,
            source_split=BENCHMARK_SOURCE_SPLIT,
            project_role=BENCHMARK_PROJECT_ROLE,
            image_dir=img_dir,
            image_count=unique_images,
            annotated_frame_count=0,
            annotation_files=ann_files,
            class_image_counts={},
            class_box_counts={},
            message=f"BDD100K failed to load from {root}: {exc}",
        )


class BDD100KDataset:
    """Shared BDD100K `val`-only dataset adapter and indexer used by Level 1, Level 2A, and Level 3B."""

    def __init__(
        self,
        root_dir: str | Path | None = None,
        split: str = "val",
    ) -> None:
        norm_split = split.strip().lower()
        if norm_split != "val":
            raise BDD100KDataSplitError(
                f"Forbidden BDD100K split '{split}'. Challenge generation MUST use 'val' split only; "
                f"BDD100K 'train' is strictly reserved for future AI solver training."
            )
        self.root_dir = resolve_bdd100k_root(root_dir)
        self.source_split = BENCHMARK_SOURCE_SPLIT
        self.source_dataset = BENCHMARK_SOURCE_DATASET
        self.project_role = BENCHMARK_PROJECT_ROLE
        self.image_dir: Path | None = None
        self.annotation_files: list[Path] = []
        self.frames: list[BDD100KFrameRecord] = []
        self._by_name: dict[str, BDD100KFrameRecord] = {}
        self._load_index()

    def _load_index(self) -> None:
        if not self.root_dir.exists():
            raise BDD100KNotFoundError(
                f"BDD100K dataset directory not found at '{self.root_dir}'.\n"
                f"To use Level 1, Level 2A, or Level 3B, provide real BDD100K validation images and annotations at:\n"
                f"  - {self.root_dir / 'images' / '100k' / 'val'}\n"
                f"  - {self.root_dir / 'labels'}\n"
                f"Or point to an existing BDD100K installation via --bdd100k-root or BDD100K_ROOT."
            )

        image_map, img_dir = _discover_val_images(self.root_dir, split=self.source_split)
        ann_files = _discover_val_annotation_files(self.root_dir, split=self.source_split)
        self.image_dir = img_dir
        self.annotation_files = ann_files

        if not image_map or not ann_files:
            raise BDD100KNotFoundError(
                f"BDD100K validation dataset is missing at '{self.root_dir}' "
                f"(found {len(set(image_map.values()))} val images, {len(ann_files)} val annotation files).\n"
                f"Place BDD100K val images in '{self.root_dir / 'images'}' and BDD100K detection label JSON "
                f"files in '{self.root_dir / 'labels'}', or pass --bdd100k-root <path>."
            )

        frames_by_name: dict[str, BDD100KFrameRecord] = {}
        for ann_path in ann_files:
            _assert_not_train_path(ann_path, self.root_dir)
            self._parse_annotation_file(ann_path, image_map, frames_by_name)

        if not frames_by_name:
            raise BDD100KNotFoundError(
                f"No BDD100K validation frames in {ann_files} matched existing val image files under '{self.root_dir}'."
            )

        self.frames = [frames_by_name[k] for k in sorted(frames_by_name.keys())]
        self._by_name = frames_by_name

    def _format_source_relpath(self, img_path: Path) -> str:
        _assert_not_train_path(img_path, self.root_dir)
        try:
            return img_path.resolve().relative_to(self.root_dir.resolve()).as_posix()
        except ValueError:
            return img_path.name

    def _parse_annotation_file(
        self,
        ann_path: Path,
        image_map: dict[str, Path],
        out_frames: dict[str, BDD100KFrameRecord],
    ) -> None:
        if ann_path.suffix.lower() == ".jsonl":
            raw_items: list[dict[str, Any]] = []
            with ann_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        raw_items.append(json.loads(line))
            self._ingest_scalabel_frames(raw_items, image_map, out_frames)
            return

        with ann_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        if isinstance(payload, list):
            self._ingest_scalabel_frames(payload, image_map, out_frames)
        elif isinstance(payload, dict):
            if "frames" in payload and isinstance(payload["frames"], list):
                self._ingest_scalabel_frames(payload["frames"], image_map, out_frames)
            elif "images" in payload and "annotations" in payload:
                self._ingest_coco_format(payload, image_map, out_frames)
            elif "name" in payload:
                self._ingest_scalabel_frames([payload], image_map, out_frames)

    def _ingest_scalabel_frames(
        self,
        items: list[dict[str, Any]],
        image_map: dict[str, Path],
        out_frames: dict[str, BDD100KFrameRecord],
    ) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_name = str(item.get("name") or item.get("file_name") or "").strip()
            if not raw_name:
                continue
            basename = Path(raw_name).name
            stem = Path(raw_name).stem
            img_path = image_map.get(basename) or image_map.get(stem)
            if img_path is None:
                continue

            rel_source_path = self._format_source_relpath(img_path)
            attrs = item.get("attributes") or {}
            weather = str(attrs.get("weather", "undefined")).lower()
            scene = str(attrs.get("scene", "undefined")).lower()
            timeofday = str(attrs.get("timeofday", "undefined")).lower()
            frame_w = int(item.get("width") or 1280)
            frame_h = int(item.get("height") or 720)

            raw_labels = item.get("labels")
            if raw_labels is None:
                frames_sub = item.get("frames")
                if isinstance(frames_sub, list) and frames_sub:
                    raw_labels = frames_sub[0].get("objects", [])
                else:
                    raw_labels = []

            objects: list[BDD100KObjectAnnotation] = []
            for lbl in raw_labels or []:
                if not isinstance(lbl, dict):
                    continue
                box = lbl.get("box2d")
                if not isinstance(box, dict):
                    continue
                raw_cat = str(lbl.get("category", "")).strip()
                if not raw_cat:
                    continue
                norm_cat = normalize_bdd100k_category(raw_cat)
                lbl_attrs = lbl.get("attributes") or {}
                occluded = bool(lbl_attrs.get("occluded", False))
                truncated = bool(lbl_attrs.get("truncated", False))
                tl_color = str(lbl_attrs.get("trafficLightColor", "none"))

                x1 = float(box.get("x1", 0.0))
                y1 = float(box.get("y1", 0.0))
                x2 = float(box.get("x2", 0.0))
                y2 = float(box.get("y2", 0.0))
                if x2 <= x1 or y2 <= y1:
                    continue

                objects.append(
                    BDD100KObjectAnnotation(
                        category=norm_cat,
                        raw_category=raw_cat,
                        box2d=(x1, y1, x2, y2),
                        occluded=occluded,
                        truncated=truncated,
                        traffic_light_color=tl_color,
                        frame_width=frame_w,
                        frame_height=frame_h,
                    )
                )

            out_frames[img_path.name] = BDD100KFrameRecord(
                name=img_path.name,
                image_path=img_path,
                source_path=rel_source_path,
                source_split=BENCHMARK_SOURCE_SPLIT,
                source_dataset=BENCHMARK_SOURCE_DATASET,
                project_role=BENCHMARK_PROJECT_ROLE,
                sequence_id=extract_sequence_id(img_path.name),
                weather=weather,
                scene=scene,
                timeofday=timeofday,
                frame_width=frame_w,
                frame_height=frame_h,
                objects=objects,
            )

    def _ingest_coco_format(
        self,
        payload: dict[str, Any],
        image_map: dict[str, Path],
        out_frames: dict[str, BDD100KFrameRecord],
    ) -> None:
        cat_map: dict[int, str] = {}
        for c in payload.get("categories", []):
            cat_map[int(c["id"])] = str(c["name"])

        img_id_to_record: dict[int, BDD100KFrameRecord] = {}
        for im in payload.get("images", []):
            fname = Path(str(im.get("file_name", ""))).name
            stem = Path(fname).stem
            img_path = image_map.get(fname) or image_map.get(stem)
            if img_path is None:
                continue
            rel_source_path = self._format_source_relpath(img_path)
            attrs = im.get("attributes") or {}
            rec = BDD100KFrameRecord(
                name=img_path.name,
                image_path=img_path,
                source_path=rel_source_path,
                source_split=BENCHMARK_SOURCE_SPLIT,
                source_dataset=BENCHMARK_SOURCE_DATASET,
                project_role=BENCHMARK_PROJECT_ROLE,
                sequence_id=extract_sequence_id(img_path.name),
                weather=str(attrs.get("weather", "undefined")).lower(),
                scene=str(attrs.get("scene", "undefined")).lower(),
                timeofday=str(attrs.get("timeofday", "undefined")).lower(),
                frame_width=int(im.get("width") or 1280),
                frame_height=int(im.get("height") or 720),
            )
            img_id_to_record[int(im["id"])] = rec
            out_frames[rec.name] = rec

        for ann in payload.get("annotations", []):
            img_id = int(ann.get("image_id", -1))
            if img_id not in img_id_to_record:
                continue
            rec = img_id_to_record[img_id]
            raw_cat = cat_map.get(int(ann.get("category_id", -1)), "")
            if not raw_cat:
                continue
            bbox = ann.get("bbox")
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            x1, y1, w, h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            if w <= 0 or h <= 0:
                continue
            attrs = ann.get("attributes") or {}
            rec.objects.append(
                BDD100KObjectAnnotation(
                    category=normalize_bdd100k_category(raw_cat),
                    raw_category=raw_cat,
                    box2d=(x1, y1, x1 + w, y1 + h),
                    occluded=bool(attrs.get("occluded", False)),
                    truncated=bool(attrs.get("truncated", False)),
                    frame_width=rec.frame_width,
                    frame_height=rec.frame_height,
                )
            )

    def class_statistics(self) -> tuple[dict[str, int], dict[str, int]]:
        """Return `(image_counts_by_class, box_counts_by_class)` across all indexed validation frames."""
        img_counts: Counter[str] = Counter()
        box_counts: Counter[str] = Counter()
        for frame in self.frames:
            seen_in_frame: set[str] = set()
            for obj in frame.objects:
                box_counts[obj.category] += 1
                seen_in_frame.add(obj.category)
            for cat in seen_in_frame:
                img_counts[cat] += 1
        return dict(img_counts.most_common()), dict(box_counts.most_common())

    def get_frame(self, name: str) -> BDD100KFrameRecord | None:
        basename = Path(name).name
        if basename in self._by_name:
            return self._by_name[basename]
        for rec in self.frames:
            if Path(rec.name).stem == Path(name).stem:
                return rec
        return None

    def load_image(self, frame: BDD100KFrameRecord) -> Image.Image:
        """Open and return an RGB copy of a BDD100K `val` frame without modifying the source file."""
        if frame.source_split != "val":
            raise BDD100KDataSplitError(
                f"Frame '{frame.name}' has source_split='{frame.source_split}', expected 'val'."
            )
        _assert_not_train_path(frame.image_path, self.root_dir)
        with Image.open(frame.image_path) as img:
            return img.convert("RGB")

    def select_easy_grid_samples(
        self,
        rng: DeterministicRNG,
        target_class: str,
        total_tiles: int,
        positive_count: int,
        min_easy_area_ratio: float = 0.012,
        allow_duplicates: bool = False,
    ) -> list[tuple[BDD100KFrameRecord, bool, dict[str, Any]]]:
        """Select easy, clearly visible BDD100K `val` positive and negative examples for Level 1 / Level 3B."""
        if not (1 <= positive_count < total_tiles):
            raise ValueError(
                f"positive_count ({positive_count}) must be between 1 and {total_tiles - 1}"
            )
        negative_count = total_tiles - positive_count

        easy_positives: list[tuple[BDD100KFrameRecord, dict[str, Any]]] = []
        fallback_positives: list[tuple[BDD100KFrameRecord, dict[str, Any]]] = []
        clear_negatives: list[tuple[BDD100KFrameRecord, dict[str, Any]]] = []
        fallback_negatives: list[tuple[BDD100KFrameRecord, dict[str, Any]]] = []

        for frame in self.frames:
            meta = frame.evaluate_for_target(
                target_class, min_easy_area_ratio=min_easy_area_ratio
            )
            if meta["is_positive"]:
                if meta["is_microscopic_positive"]:
                    continue
                if meta["is_easy_positive"]:
                    easy_positives.append((frame, meta))
                elif not meta["is_borderline_small_positive"]:
                    fallback_positives.append((frame, meta))
            else:
                if meta["is_ambiguous_negative"]:
                    continue
                if meta["is_clear_negative"]:
                    clear_negatives.append((frame, meta))
                else:
                    fallback_negatives.append((frame, meta))

        pos_pool = (
            easy_positives
            if len(easy_positives) >= positive_count
            else (easy_positives + fallback_positives)
        )
        neg_pool = (
            clear_negatives
            if len(clear_negatives) >= negative_count
            else (clear_negatives + fallback_negatives)
        )

        selected_pos = self._sample_pool(
            rng.fork("easy_pos"), pos_pool, positive_count, allow_duplicates
        )
        selected_neg = self._sample_pool(
            rng.fork("easy_neg"), neg_pool, negative_count, allow_duplicates
        )

        combined: list[tuple[BDD100KFrameRecord, bool, dict[str, Any]]] = [
            *[(f, True, m) for f, m in selected_pos],
            *[(f, False, m) for f, m in selected_neg],
        ]
        return rng.fork("shuffle").shuffle(combined)

    def select_hard_grid_samples(
        self,
        rng: DeterministicRNG,
        target_class: str,
        total_tiles: int,
        positive_count: int,
        preferred_attributes: Sequence[str] | None = None,
        min_easy_area_ratio: float = 0.012,
        allow_duplicates: bool = False,
    ) -> list[tuple[BDD100KFrameRecord, bool, dict[str, Any]]]:
        """Select difficult real BDD100K `val` positive scenes and strong distractor negatives for Level 2A."""
        if not (1 <= positive_count < total_tiles):
            raise ValueError(
                f"positive_count ({positive_count}) must be between 1 and {total_tiles - 1}"
            )
        negative_count = total_tiles - positive_count
        pref_set = set(preferred_attributes or [])

        fair_hard_positives: list[tuple[int, BDD100KFrameRecord, dict[str, Any]]] = []
        borderline_hard_positives: list[tuple[int, BDD100KFrameRecord, dict[str, Any]]] = []
        other_positives: list[tuple[int, BDD100KFrameRecord, dict[str, Any]]] = []
        negatives_scored: list[tuple[int, BDD100KFrameRecord, dict[str, Any]]] = []

        for frame in self.frames:
            meta = frame.evaluate_for_target(
                target_class, min_easy_area_ratio=min_easy_area_ratio
            )
            tags = set(meta["difficulty_tags"])
            pref_matches = len(tags & pref_set) if pref_set else len(tags)
            tier_score = pref_matches * 10 + int(meta["hard_score"])

            if meta["is_positive"]:
                if meta["is_microscopic_positive"]:
                    continue
                if meta["is_hard_positive"]:
                    if meta["is_borderline_small_positive"]:
                        borderline_hard_positives.append((tier_score, frame, meta))
                    else:
                        fair_hard_positives.append((tier_score, frame, meta))
                else:
                    other_positives.append((tier_score, frame, meta))
            else:
                if meta["is_ambiguous_negative"]:
                    continue
                negatives_scored.append((tier_score, frame, meta))

        if len(fair_hard_positives) >= positive_count:
            pos_candidates = fair_hard_positives
        elif len(fair_hard_positives) + len(borderline_hard_positives) >= positive_count:
            pos_candidates = fair_hard_positives + borderline_hard_positives
        else:
            pos_candidates = fair_hard_positives + borderline_hard_positives + other_positives

        selected_pos = self._sample_tiered_pool(
            rng.fork("hard_pos"),
            pos_candidates,
            positive_count,
            allow_duplicates,
        )
        selected_neg = self._sample_tiered_pool(
            rng.fork("hard_neg"),
            negatives_scored,
            negative_count,
            allow_duplicates,
        )

        combined: list[tuple[BDD100KFrameRecord, bool, dict[str, Any]]] = [
            *[(f, True, m) for f, m in selected_pos],
            *[(f, False, m) for f, m in selected_neg],
        ]
        return rng.fork("shuffle").shuffle(combined)

    @staticmethod
    def _sample_pool(
        rng: DeterministicRNG,
        pool: list[tuple[BDD100KFrameRecord, dict[str, Any]]],
        count: int,
        allow_duplicates: bool,
    ) -> list[tuple[BDD100KFrameRecord, dict[str, Any]]]:
        if not pool:
            raise BDD100KNotFoundError("No matching BDD100K validation frames found in candidate pool")
        if not allow_duplicates and len(pool) < count:
            raise ValueError(
                f"Insufficient unique BDD100K validation frames in pool: needed {count}, found {len(pool)}"
            )
        if allow_duplicates:
            return [rng.choice(pool) for _ in range(count)]
        return rng.sample(pool, count)

    @staticmethod
    def _sample_tiered_pool(
        rng: DeterministicRNG,
        scored_pool: list[tuple[int, BDD100KFrameRecord, dict[str, Any]]],
        count: int,
        allow_duplicates: bool,
    ) -> list[tuple[BDD100KFrameRecord, dict[str, Any]]]:
        if not scored_pool:
            raise BDD100KNotFoundError("No matching BDD100K validation frames found in candidate pool")
        if not allow_duplicates and len(scored_pool) < count:
            raise ValueError(
                f"Insufficient unique BDD100K validation frames in pool: needed {count}, found {len(scored_pool)}"
            )

        tiers: dict[int, list[tuple[BDD100KFrameRecord, dict[str, Any]]]] = {}
        for score, frame, meta in scored_pool:
            tiers.setdefault(score, []).append((frame, meta))

        ordered: list[tuple[BDD100KFrameRecord, dict[str, Any]]] = []
        for score in sorted(tiers.keys(), reverse=True):
            shuffled_tier = rng.fork(f"tier_{score}").shuffle(tiers[score])
            ordered.extend(shuffled_tier)

        if not allow_duplicates:
            return ordered[:count]
        return [rng.choice(ordered) for _ in range(count)]
