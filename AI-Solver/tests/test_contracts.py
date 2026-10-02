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
