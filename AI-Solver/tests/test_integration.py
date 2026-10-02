"""Explicitly enabled public reads only; no VLM credentials or submissions."""

import os

import pytest

from ai_solver.client import BenchmarkClient
from ai_solver.runner import select_entries


@pytest.mark.integration
def test_public_level1_assets():
    if os.getenv("RUN_AI_SOLVER_INTEGRATION") != "1" or not os.getenv("CAPTCHA_BASE_URL"):
        pytest.skip("Set RUN_AI_SOLVER_INTEGRATION=1 and CAPTCHA_BASE_URL for public reads")
    with BenchmarkClient(os.environ["CAPTCHA_BASE_URL"], timeout=30) as client:
        entries = select_entries(client.get_catalog(), "street-grid")
        assert entries, "No street-grid challenges discovered"
        asset_count = 0
        # An opt-in full public asset preflight proves all discovered Level 1 tiles download.
        for entry in entries:
            challenge = client.get_challenge(entry)
            assets = client.download_assets(challenge)
            assert len(assets) == len(challenge.assets) and all(assets)
            asset_count += len(assets)
        print(f"Public integration: {len(entries)} street-grid challenges; {asset_count} assets")
