"""Pydantic schemas for configurations, public challenges, private ground-truth answers, and the benchmark manifest."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

LEVEL_1_KEY = "level_1_street_grid"
LEVEL_2A_KEY = "level_2a_hard_street_grid"
LEVEL_2B_KEY = "level_2b_checker_shadow"
# Legacy internal identifier; the current public variant is routing-puzzle.
LEVEL_3A_KEY = "level_3a_tangled_cables"
LEVEL_3B_KEY = "level_3b_degraded_vision"

ALL_LEVEL_KEYS: tuple[str, ...] = (
    LEVEL_1_KEY,
    LEVEL_2A_KEY,
    LEVEL_2B_KEY,
    LEVEL_3A_KEY,
    LEVEL_3B_KEY,
)

LEVEL_DIR_NAMES: dict[str, str] = {
    LEVEL_1_KEY: "level-1",
    LEVEL_2A_KEY: "level-2a",
    LEVEL_2B_KEY: "level-2b",
    LEVEL_3A_KEY: "level-3a",
    LEVEL_3B_KEY: "level-3b",
}

_LEVEL_ALIASES: dict[str, str] = {
    "1": LEVEL_1_KEY,
    "lvl1": LEVEL_1_KEY,
    "level1": LEVEL_1_KEY,
    "level-1": LEVEL_1_KEY,
    "level_1": LEVEL_1_KEY,
    "street-grid": LEVEL_1_KEY,
    LEVEL_1_KEY: LEVEL_1_KEY,
    "2a": LEVEL_2A_KEY,
    "lvl2a": LEVEL_2A_KEY,
    "level2a": LEVEL_2A_KEY,
    "level-2a": LEVEL_2A_KEY,
    "level_2a": LEVEL_2A_KEY,
    "hard-street-grid": LEVEL_2A_KEY,
    LEVEL_2A_KEY: LEVEL_2A_KEY,
    "2b": LEVEL_2B_KEY,
    "lvl2b": LEVEL_2B_KEY,
    "level2b": LEVEL_2B_KEY,
    "level-2b": LEVEL_2B_KEY,
    "level_2b": LEVEL_2B_KEY,
    "checker-shadow": LEVEL_2B_KEY,
    LEVEL_2B_KEY: LEVEL_2B_KEY,
    "3a": LEVEL_3A_KEY,
    "lvl3a": LEVEL_3A_KEY,
    "level3a": LEVEL_3A_KEY,
    "level-3a": LEVEL_3A_KEY,
    "level_3a": LEVEL_3A_KEY,
    "tangled-cables": LEVEL_3A_KEY,
    "routing-puzzle": LEVEL_3A_KEY,
    "routing-puzzles": LEVEL_3A_KEY,
    "routing": LEVEL_3A_KEY,
    "level_3a_routing_puzzles": LEVEL_3A_KEY,
    LEVEL_3A_KEY: LEVEL_3A_KEY,
    "3b": LEVEL_3B_KEY,
    "lvl3b": LEVEL_3B_KEY,
    "level3b": LEVEL_3B_KEY,
    "level-3b": LEVEL_3B_KEY,
    "level_3b": LEVEL_3B_KEY,
    "degraded-vision": LEVEL_3B_KEY,
    LEVEL_3B_KEY: LEVEL_3B_KEY,
}

VARIANT_TO_LEVEL_KEY: dict[str, str] = {
    "street-grid": LEVEL_1_KEY,
    "hard-street-grid": LEVEL_2A_KEY,
    "checker-shadow": LEVEL_2B_KEY,
    "tangled-cables": LEVEL_3A_KEY,
    "routing-puzzle": LEVEL_3A_KEY,
    "degraded-vision": LEVEL_3B_KEY,
}


def normalize_level_key(raw: str) -> str:
    """Resolve user-provided level identifier (e.g., '1', '2a', 'level_3b_degraded_vision') to canonical key."""
    key = raw.strip().lower()
    if key not in _LEVEL_ALIASES:
        valid = ", ".join(["1", "2a", "2b", "3a", "3b", *ALL_LEVEL_KEYS])
        raise ValueError(f"Unknown level '{raw}'. Expected one of: {valid}")
    return _LEVEL_ALIASES[key]


class PublicUIConfig(BaseModel):
    """UI layout and interaction metadata exposed in challenge.json."""

    model_config = ConfigDict(extra="forbid")

    rows: int = Field(..., ge=1)
    columns: int = Field(..., ge=1)
    selectionMode: Literal["multiple", "single"]
    options: list[str] | None = None


class PublicChallenge(BaseModel):
    """Universal PUBLIC challenge contract written to challenge.json."""

    model_config = ConfigDict(extra="forbid")

    schemaVersion: int = Field(default=1, ge=1)
    id: str = Field(..., min_length=3)
    level: Literal[1, 2, 3]
    variant: Literal[
        "street-grid",
        "hard-street-grid",
        "checker-shadow",
        "tangled-cables",
        "routing-puzzle",
        "degraded-vision",
    ]
    subtype: str | None = None
    difficulty: Literal["easy", "medium", "story", "hard", "extreme"] | None = None
    type: Literal["image-selection", "single-choice"]
    instruction: str = Field(..., min_length=5)
    seed: int
    assets: list[str] = Field(..., min_length=1)
    ui: PublicUIConfig


class TransformationSpec(BaseModel):
    """Transformation parameters recorded in Level 3B private metadata."""

    model_config = ConfigDict(extra="forbid")

    type: str = "downsample_upscale"
    resolution: int = Field(..., ge=1)
    upscale: Literal["nearest", "bilinear", "bicubic"] = "nearest"
    colorQuantization: int | None = None
    blurRadius: float = 0.0
    contrastFactor: float = 1.0
    jpegQuality: int | None = None
    partialMaskRatio: float = 0.0


class DegradationInfo(BaseModel):
    """Detailed resolution degradation metadata for Level 3B."""

    model_config = ConfigDict(extra="forbid")

    method: str = "downsample_upscale"
    downsampleWidth: int = Field(..., ge=1)
    downsampleHeight: int = Field(..., ge=1)
    upscaleMethod: Literal["nearest", "bilinear", "bicubic"] = "nearest"
    colorQuantization: int | None = None
    blurRadius: float = 0.0
    contrastFactor: float = 1.0
    jpegQuality: int | None = None
    partialMaskRatio: float = 0.0


class TilePrivateMetadata(BaseModel):
    """Private ground-truth metadata for a single BDD100K validation tile in a grid challenge."""

    model_config = ConfigDict(extra="forbid")

    tileIndex: int = Field(..., ge=0)
    asset: str
    sourceId: str
    sourceImage: str
    source_image_id: str = ""
    source_path: str = ""
    source_dataset: str = "BDD100K"
    source_split: str = "val"
    project_role: str = "held_out_benchmark"
    sequence_id: str | None = None
    datasetSource: str = "bdd100k"
    targetClass: str
    classes: list[str]
    difficulty: str
    attributes: list[str] = Field(default_factory=list)
    maxTargetAreaRatio: float = 0.0
    weather: str = "undefined"
    timeofday: str = "undefined"
    isPositive: bool
    transformation: TransformationSpec | None = None
    degradation: DegradationInfo | None = None

    @model_validator(mode="after")
    def _populate_source_defaults(self) -> "TilePrivateMetadata":
        if not self.source_image_id:
            self.source_image_id = self.sourceId
        if not self.source_path:
            self.source_path = f"images/100k/val/{self.sourceImage}"
        return self


class Level2BAssetMetadata(BaseModel):
    """Schema for `assets/level-2b/metadata.json` documenting the existing Adelson asset."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1)
    author: str | None = None
    source: str = Field(..., min_length=1)
    license: str = Field(..., min_length=1)
    asset_file: str = "checker-shadow.png"
    question: str = "Are squares A and B the same shade?"
    answer: str = "yes"
    options: list[str] = Field(default_factory=lambda: ["Yes", "No"])
    regions: dict[str, list[int]] | None = None


class SquareMeasurement(BaseModel):
    """Private measurement metadata for a marked square in the Level 2B Adelson asset."""

    model_config = ConfigDict(extra="forbid")

    label: str
    safeInteriorBox: list[int]
    measuredRgb: list[float]
    measuredLuminance: float


class IllusionMetadata(BaseModel):
    """Private evaluation metadata for Level 2B Adelson Checker Shadow Illusion."""

    model_config = ConfigDict(extra="forbid")

    assetName: str
    source: str
    license: str
    assetFile: str
    proceduralGenerationUsed: bool = False
    squareA: SquareMeasurement
    squareB: SquareMeasurement
    luminanceDifference: float
    rgbMaxDifference: float
    tolerance: float


class CableQuery(BaseModel):
    """Query specification for Level 3A Tangled Cables."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "find_source",
        "find-source",
        "find_destination",
        "find-destination",
    ]
    target: str


class CableIntersection(BaseModel):
    """Intersection metadata between two cables in Level 3A."""

    model_config = ConfigDict(extra="forbid")

    point: list[float]
    overCable: str
    underCable: str


class CableAnnotations(BaseModel):
    """Private geometric annotations for Level 3A Tangled Cables."""

    model_config = ConfigDict(extra="forbid")

    canvasDimensions: list[int]
    endpointPositions: dict[str, dict[str, list[float]]]
    controlPoints: dict[str, list[list[float]]] | None = None
    centerlines: dict[str, list[list[float]]]
    cableMasks: dict[str, dict[str, Any]]
    intersections: list[CableIntersection]
    layerOrder: list[str]
    difficultyMetadata: dict[str, Any] | None = None


class PrivateAnswer(BaseModel):
    """Universal PRIVATE ground-truth contract written to answer.json."""

    model_config = ConfigDict(extra="forbid")

    challengeId: str = Field(..., min_length=3)
    levelKey: str | None = None
    datasetSource: str | None = None
    dataset: str | None = None
    source_dataset: str | None = None
    source_split: str | None = None
    project_role: str | None = None
    source_image_id: str | None = None
    source_path: str | None = None
    sequence_id: str | None = None
    correctSelection: list[int] = Field(default_factory=list)
    answer: str | list[int] | None = None
    targetClass: str | None = None
    target: str | None = None
    source_image: str | None = None
    sourceImage: str | None = None
    transformation: TransformationSpec | None = None
    degradation: DegradationInfo | None = None
    tiles: list[TilePrivateMetadata] | None = None
    illusion: IllusionMetadata | None = None
    connections: dict[str, str] | None = None
    query: CableQuery | None = None
    annotations: CableAnnotations | None = None
    subtype: str | None = None
    routing: dict[str, Any] | None = None


class BenchmarkManifestEntry(BaseModel):
    """Single BDD100K `val` image entry in the held-out benchmark manifest."""

    model_config = ConfigDict(extra="forbid")

    source_image_id: str
    source_path: str
    source_split: Literal["val"] = "val"
    source_dataset: str = "BDD100K"
    project_role: str = "held_out_benchmark"
    sequence_id: str | None = None
    used_by: list[str] = Field(default_factory=list)
    challenge_ids: list[str] = Field(default_factory=list)


class BenchmarkManifest(BaseModel):
    """Held-out BDD100K validation benchmark manifest tracking all images used across Levels 1, 2A, and 3B."""

    model_config = ConfigDict(extra="forbid")

    dataset: str = "BDD100K"
    source_dataset: str = "BDD100K"
    source_split: Literal["val"] = "val"
    project_role: str = "held_out_benchmark"
    total_unique_images: int = 0
    total_unique_sequences: int = 0
    sequences: list[str] = Field(default_factory=list)
    images: list[BenchmarkManifestEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Level Configuration Schemas
# ---------------------------------------------------------------------------


def _validate_val_only_split(split_val: str) -> str:
    cleaned = split_val.strip().lower()
    if cleaned != "val":
        raise ValueError(
            f"Invalid BDD100K sourceSplit '{split_val}'. Only 'val' is allowed for challenge generation; "
            f"'train' is strictly reserved for future AI solver training."
        )
    return "val"


class Level1Config(BaseModel):
    """Configuration for Level 1 — Normal Street CAPTCHA (BDD100K `val` easy samples)."""

    model_config = ConfigDict(extra="forbid")

    gridRows: int = Field(default=3, ge=2, le=6)
    gridColumns: int = Field(default=3, ge=2, le=6)
    target: str = Field(default="motorcycle", min_length=1)
    positiveCount: int | None = Field(default=None, ge=1)
    positiveCountRange: tuple[int, int] = (2, 4)
    minEasyAreaRatio: float = Field(default=0.012, ge=0.001, le=0.5)
    tileWidth: int = Field(default=256, ge=64, le=1024)
    tileHeight: int = Field(default=256, ge=64, le=1024)
    allowDuplicates: bool = False
    bdd100kRoot: str = "data/bdd100k"
    sourceSplit: str = "val"

    @model_validator(mode="after")
    def _validate_counts(self) -> "Level1Config":
        self.sourceSplit = _validate_val_only_split(self.sourceSplit)
        total = self.gridRows * self.gridColumns
        low, high = self.positiveCountRange
        if low < 1 or high < low or high >= total:
            raise ValueError(
                f"positiveCountRange {self.positiveCountRange} must satisfy 1 <= min <= max < {total}"
            )
        if self.positiveCount is not None and not (1 <= self.positiveCount < total):
            raise ValueError(f"positiveCount ({self.positiveCount}) must be in 1..{total - 1}")
        return self


class Level2AConfig(BaseModel):
    """Configuration for Level 2A — Hard Street CAPTCHA (BDD100K `val` difficult samples)."""

    model_config = ConfigDict(extra="forbid")

    gridSize: int | None = Field(default=4, ge=3, le=6)
    gridRows: int | None = Field(default=None, ge=3, le=6)
    gridColumns: int | None = Field(default=None, ge=3, le=6)
    target: str = Field(default="motorcycle", min_length=1)
    positiveCount: int | None = Field(default=5, ge=1)
    positiveCountRange: tuple[int, int] | None = None
    preferredAttributes: list[str] = Field(
        default_factory=lambda: [
            "small-object",
            "occluded",
            "truncated",
            "night",
            "low-light",
            "rain",
            "dense-traffic",
            "confusable-object",
            "distant-object",
            "unusual-angle",
        ]
    )
    minEasyAreaRatio: float = Field(default=0.012, ge=0.001, le=0.5)
    tileWidth: int = Field(default=256, ge=64, le=1024)
    tileHeight: int = Field(default=256, ge=64, le=1024)
    allowDuplicates: bool = False
    bdd100kRoot: str = "data/bdd100k"
    sourceSplit: str = "val"

    @property
    def resolved_rows(self) -> int:
        return self.gridRows or self.gridSize or 4

    @property
    def resolved_columns(self) -> int:
        return self.gridColumns or self.gridSize or 4

    @model_validator(mode="after")
    def _validate_grid(self) -> "Level2AConfig":
        self.sourceSplit = _validate_val_only_split(self.sourceSplit)
        total = self.resolved_rows * self.resolved_columns
        if self.positiveCount is not None and not (1 <= self.positiveCount < total):
            raise ValueError(f"positiveCount ({self.positiveCount}) must be in 1..{total - 1}")
        if self.positiveCountRange is not None:
            low, high = self.positiveCountRange
            if low < 1 or high < low or high >= total:
                raise ValueError(
                    f"positiveCountRange {self.positiveCountRange} must be within 1..{total - 1}"
                )
        return self


class Level2BConfig(BaseModel):
    """Configuration for Level 2B — Adelson Checker Shadow Illusion (existing static asset)."""

    model_config = ConfigDict(extra="forbid")

    assetPath: str = "assets/level-2b/checker-shadow.png"
    metadataPath: str = "assets/level-2b/metadata.json"
    instruction: str = "Are squares A and B the same shade?"
    options: list[str] = Field(default_factory=lambda: ["Yes", "No"])
    luminanceTolerance: float = Field(default=1.0, ge=0.0, le=5.0)

    @model_validator(mode="after")
    def _validate_options(self) -> "Level2BConfig":
        if not any(opt.lower() == "yes" for opt in self.options):
            raise ValueError("options must include 'Yes'")
        return self


class LaserMazeSubtypeConfig(BaseModel):
    """Subtype configuration for Laser Maze puzzle."""

    model_config = ConfigDict(extra="ignore")
    gridSize: tuple[int, int] | None = None
    reflectionsRange: tuple[int, int] | None = None
    targetCount: int | None = None
    distractorMirrors: tuple[int, int] | None = None


class ConveyorRoutingSubtypeConfig(BaseModel):
    """Subtype configuration for Conveyor Routing puzzle."""

    model_config = ConfigDict(extra="ignore")
    switchCount: int | None = None
    routeDecisionDepth: int | None = Field(default=None, ge=2, le=12)
    totalSwitchCount: int | None = Field(default=None, ge=3, le=22)
    binCount: int | None = None
    decoyBranches: int | None = None


class PipeFlowSubtypeConfig(BaseModel):
    """Subtype configuration for Pipe Flow routing puzzle."""

    model_config = ConfigDict(extra="ignore")
    junctionCount: int | None = None
    solutionDecisionDepth: int | None = Field(default=None, ge=2, le=12)
    totalJunctionCount: int | None = Field(default=None, ge=3, le=20)
    decoyBranchCount: int | None = Field(default=None, ge=1, le=10)
    tankCount: int | None = None
    closedValves: int | None = None


class DeviceCablesSubtypeConfig(BaseModel):
    """Subtype configuration for Device Cables routing puzzle."""

    model_config = ConfigDict(extra="ignore")
    cableCountRange: tuple[int, int] | None = None
    waypointRange: tuple[int, int] | None = None
    lineWidth: int | None = None
    answerOptionCountRange: tuple[int, int] | None = None


ROUTING_DIFFICULTY_PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "laser-maze": {
        "easy": {'grid': (7, 7), 'reflections': (1, 2), 'targets': 3, 'distractors': (0, 2)},
        "medium": {'grid': (8, 8), 'reflections': (3, 4), 'targets': 4, 'distractors': (2, 4)},
        "story": {'grid': (10, 10), 'reflections': (5, 6), 'targets': 5, 'distractors': (4, 6)},
        "hard": {'grid': (11, 11), 'reflections': (7, 8), 'targets': 5, 'distractors': (6, 8)},
        "extreme": {'grid': (12, 12), 'reflections': (9, 12), 'targets': 6, 'distractors': (8, 10)},
    },
    "conveyor-routing": {
        "easy": {'routeDecisionDepth': 2, 'totalSwitchCount': 4, 'bins': 3, 'decoyBranchCount': 1},
        "medium": {'routeDecisionDepth': 4, 'totalSwitchCount': 7, 'bins': 4, 'decoyBranchCount': 2},
        "story": {'routeDecisionDepth': 6, 'totalSwitchCount': 11, 'bins': 5, 'decoyBranchCount': 4},
        "hard": {'routeDecisionDepth': 8, 'totalSwitchCount': 14, 'bins': 5, 'decoyBranchCount': 5},
        "extreme": {'routeDecisionDepth': 11, 'totalSwitchCount': 20, 'bins': 6, 'decoyBranchCount': 7},
    },
    "pipe-flow": {
        "easy": {'solutionDecisionDepth': 2, 'totalJunctionCount': 4, 'tanks': 3, 'criticalClosedValveCount': 1, 'decoyBranchCount': 1},
        "medium": {'solutionDecisionDepth': 4, 'totalJunctionCount': 6, 'tanks': 4, 'criticalClosedValveCount': 2, 'decoyBranchCount': 2},
        "story": {'solutionDecisionDepth': 6, 'totalJunctionCount': 10, 'tanks': 5, 'criticalClosedValveCount': 4, 'decoyBranchCount': 4},
        "hard": {'solutionDecisionDepth': 8, 'totalJunctionCount': 14, 'tanks': 5, 'criticalClosedValveCount': 6, 'decoyBranchCount': 6},
        "extreme": {'solutionDecisionDepth': 11, 'totalJunctionCount': 19, 'tanks': 6, 'criticalClosedValveCount': 8, 'decoyBranchCount': 8},
    },
    "device-cables": {
        "easy": {'cableCountRange': (5, 6), 'waypointRange': (2, 3), 'lineWidth': 7, 'answerOptionCountRange': (4, 4)},
        "medium": {'cableCountRange': (7, 8), 'waypointRange': (3, 4), 'lineWidth': 7, 'answerOptionCountRange': (4, 4)},
        "story": {'cableCountRange': (9, 10), 'waypointRange': (3, 5), 'lineWidth': 7, 'answerOptionCountRange': (5, 6)},
        "hard": {'cableCountRange': (10, 11), 'waypointRange': (4, 5), 'lineWidth': 7, 'answerOptionCountRange': (5, 6)},
        "extreme": {'cableCountRange': (11, 12), 'waypointRange': (5, 6), 'lineWidth': 7, 'answerOptionCountRange': (6, 6)},
    },
}

# Used only by the backward-compatible Tangled Cables generator, never routing puzzles.
LEGACY_TANGLED_CABLE_DIFFICULTY_PRESETS: dict[str, dict[str, Any]] = {
    "easy": {"cableCountRange": (8, 10), "waypointRange": (2, 4), "lineWidth": 7},
    "medium": {"cableCountRange": (12, 20), "waypointRange": (3, 5), "lineWidth": 6},
    "hard": {"cableCountRange": (20, 35), "waypointRange": (3, 7), "lineWidth": 5},
    "extreme": {"cableCountRange": (35, 50), "waypointRange": (4, 8), "lineWidth": 4},
}


class Level3AConfig(BaseModel):
    """Configuration for Level 3A — Routing Puzzles family."""

    model_config = ConfigDict(extra="ignore")

    defaultSubtype: Literal[
        "laser-maze",
        "conveyor-routing",
        "pipe-flow",
        "device-cables",
    ] = "laser-maze"
    subtype: str | None = None
    difficulty: Literal["easy", "medium", "story", "hard", "extreme"] = "medium"
    enabledSubtypes: list[str] = Field(
        default_factory=lambda: [
            "laser-maze",
            "conveyor-routing",
            "pipe-flow",
            "device-cables",
        ]
    )

    canvasWidth: int = Field(default=1200, ge=600, le=3200)
    canvasHeight: int = Field(default=800, ge=500, le=2400)

    laserMaze: LaserMazeSubtypeConfig = Field(default_factory=LaserMazeSubtypeConfig)
    conveyorRouting: ConveyorRoutingSubtypeConfig = Field(default_factory=ConveyorRoutingSubtypeConfig)
    pipeFlow: PipeFlowSubtypeConfig = Field(default_factory=PipeFlowSubtypeConfig)
    deviceCables: DeviceCablesSubtypeConfig = Field(default_factory=DeviceCablesSubtypeConfig)

    # Legacy fields preserved for compatibility:
    cableCount: int | None = Field(default=None, ge=4, le=60)
    waypointRange: tuple[int, int] = (3, 7)
    lineWidth: int = Field(default=6, ge=2, le=14)
    queryType: Literal[
        "find_source",
        "find-source",
        "find_destination",
        "find-destination",
        "auto",
    ] = "find_source"
    minEndpointSpacing: int = Field(default=16, ge=10, le=80)

    @model_validator(mode="after")
    def _validate_cables(self) -> "Level3AConfig":
        w_min, w_max = self.waypointRange
        if w_min < 1 or w_max < w_min or w_max > 12:
            raise ValueError("waypointRange must satisfy 1 <= min <= max <= 12")
        return self


SUPPORTED_3B_RESOLUTIONS = (64, 48, 32, 24, 16, 12, 8)


class Level3BConfig(BaseModel):
    """Configuration for Level 3B — Degraded Vision CAPTCHA (BDD100K `val` + controlled degradation)."""

    model_config = ConfigDict(extra="forbid")

    gridRows: int = Field(default=3, ge=2, le=6)
    gridColumns: int = Field(default=3, ge=2, le=6)
    target: str = Field(default="motorcycle", min_length=1)
    positiveCount: int = Field(default=3, ge=1)
    resolution: int = Field(default=16, ge=4, le=128)
    supportedResolutions: list[int] = Field(
        default_factory=lambda: [64, 48, 32, 24, 16, 12, 8]
    )
    batchResolutions: list[int] | None = None
    upscaleMethod: Literal["nearest", "bilinear", "bicubic"] = "nearest"
    tileWidth: int = Field(default=256, ge=64, le=1024)
    tileHeight: int = Field(default=256, ge=64, le=1024)
    colorQuantization: int | None = Field(default=None, ge=2, le=64)
    blurRadius: float = Field(default=0.0, ge=0.0, le=5.0)
    contrastFactor: float = Field(default=1.0, ge=0.2, le=2.0)
    jpegQuality: int | None = Field(default=None, ge=5, le=100)
    partialMaskRatio: float = Field(default=0.0, ge=0.0, le=0.6)
    minEasyAreaRatio: float = Field(default=0.012, ge=0.001, le=0.5)
    allowDuplicates: bool = False
    bdd100kRoot: str = "data/bdd100k"
    sourceSplit: str = "val"

    @model_validator(mode="after")
    def _validate_resolution_and_grid(self) -> "Level3BConfig":
        self.sourceSplit = _validate_val_only_split(self.sourceSplit)
        total = self.gridRows * self.gridColumns
        if not (1 <= self.positiveCount < total):
            raise ValueError(f"positiveCount ({self.positiveCount}) must be in 1..{total - 1}")
        if self.resolution not in self.supportedResolutions:
            raise ValueError(
                f"resolution {self.resolution} is not in supportedResolutions {self.supportedResolutions}"
            )
        if self.batchResolutions:
            for r in self.batchResolutions:
                if r not in self.supportedResolutions:
                    raise ValueError(
                        f"batchResolution {r} is not in supportedResolutions {self.supportedResolutions}"
                    )
        return self
