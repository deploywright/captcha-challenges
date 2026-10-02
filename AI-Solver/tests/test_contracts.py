import pytest

from ai_solver.contracts import (
    VLMSelection,
    parse_catalog,
    parse_challenge,
    validate_indices,
    validate_street_grid,
)
from ai_solver.errors import ChallengeContractError, ModelResponseError, PublicDataLeakError
from ai_solver.runner import select_entries


def test_public_contract_ignores_safe_extras(public_data):
    public_data.update(displayName="Public name", futurePublicField=True)
    result = parse_challenge(public_data)
    assert result.instruction.endswith("bus.")
    assert result.ui.rows == 3
    assert len(result.assets) == 9
    assert not hasattr(result, "futurePublicField")


@pytest.mark.parametrize("field,value", [("seed", "49"), ("assets", []), ("id", "../x")])
def test_public_contract_strict(public_data, field, value):
    public_data[field] = value
    with pytest.raises(ChallengeContractError):
        parse_challenge(public_data)


@pytest.mark.parametrize(
    "key",
    [
        "answer",
        "correctSelection",
        "routing",
        "connections",
        "solutionPath",
        "targetClass",
        "source_image_id",
        "source_path",
        "boundingBoxes",
        "cropMetadata",
        "annotations",
    ],
)
def test_recursive_public_leak(public_data, key):
    public_data["unknown"] = [{"nested": {key: "never-use"}}]
    with pytest.raises(PublicDataLeakError, match="PUBLIC DATA LEAK DETECTED"):
        parse_challenge(public_data)


def test_catalog_variant_filter_and_limit():
    entries = parse_catalog(
        [
            {"id": "hard", "level": 1, "variant": "hard-street-grid", "challengeUrl": "unused"},
            {"id": "a", "level": 1, "variant": "street-grid", "challengeUrl": "unused"},
            {"id": "b", "level": 1, "variant": "street-grid", "challengeUrl": "unused"},
        ]
    )
    assert [x.id for x in select_entries(entries, "street-grid")] == ["a", "b"]
    assert [x.id for x in select_entries(entries, "street-grid", 1)] == ["a"]


def test_duplicate_catalog_rejected():
    entry = {"id": "a", "level": 1, "variant": "street-grid", "challengeUrl": "unused"}
    with pytest.raises(ChallengeContractError, match="Duplicate"):
        parse_catalog([entry, entry])


@pytest.mark.parametrize("indices", [[-1], [9], [1, 1], [True], [1.0], ["1"], "1", None])
def test_zero_based_indices_strict(indices):
    with pytest.raises(ModelResponseError):
        validate_indices(indices, 9)


def test_zero_based_indices_sorted_and_empty():
    assert validate_indices([8, 0, 3], 9) == [0, 3, 8]
    assert validate_indices([], 9) == []
    assert VLMSelection.model_validate_json('{"selected_indices":[],"confidence":null}')


def test_dynamic_asset_count(challenge, assets):
    challenge.assets = challenge.assets[:4]
    challenge.ui.rows = challenge.ui.columns = 2
    validate_street_grid(challenge, assets[:4])
    with pytest.raises(ChallengeContractError):
        validate_street_grid(challenge, assets)


@pytest.mark.parametrize("valid_index", [0, 1, 3])
def test_validate_option_index_valid(valid_index):
    from ai_solver.contracts import validate_option_index

    assert validate_option_index(valid_index, 4) == valid_index


@pytest.mark.parametrize("invalid_index", [-1, 4, 10, True, False, 1.0, "1", None, [0]])
def test_validate_option_index_strict(invalid_index):
    from ai_solver.contracts import validate_option_index

    with pytest.raises(ModelResponseError):
        validate_option_index(invalid_index, 4)


def test_validate_challenge_and_assets_single_choice(challenge):
    from ai_solver.contracts import validate_challenge_and_assets

    challenge.variant = "routing-puzzle"
    challenge.type = "single-choice"
    challenge.ui.options = ["Server 01", "Server 02", "Server 03"]
    validate_challenge_and_assets(challenge, [b"fake_image_data"] * len(challenge.assets))

    # Invalid: fewer than 2 options
    challenge.ui.options = ["Only one"]
    with pytest.raises(ChallengeContractError, match="at least two options"):
        validate_challenge_and_assets(challenge, [b"fake_image_data"] * len(challenge.assets))

    # Invalid: options not list
    challenge.ui.options = None
    with pytest.raises(ChallengeContractError, match="at least two options"):
        validate_challenge_and_assets(challenge, [b"fake_image_data"] * len(challenge.assets))

    # Invalid: empty string in options
    challenge.ui.options = ["Server 01", "   "]
    with pytest.raises(ChallengeContractError, match="non-empty strings"):
        validate_challenge_and_assets(challenge, [b"fake_image_data"] * len(challenge.assets))


@pytest.mark.parametrize(
    "variant",
    [
        "street-grid",
        "hard-street-grid",
        "checker-shadow",
        "routing-puzzle",
        "degraded-vision",
        "all",
    ],
)
def test_run_config_variants_supported(variant):
    from ai_solver.config import RunConfig

    config = RunConfig(base_url="https://example.com", variant=variant)
    assert config.variant == variant


def test_run_config_variant_invalid():
    from pydantic import ValidationError

    from ai_solver.config import RunConfig

    with pytest.raises(ValidationError):
        RunConfig(base_url="https://example.com", variant="invalid-variant")
