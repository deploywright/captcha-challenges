"""HTTP client restricted to the benchmark's public resource allowlist."""

import json
import re
import time
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

import httpx
from pydantic import ValidationError

from .config import normalize_base_url
from .contracts import (
    CatalogEntry,
    PublicChallenge,
    SolverPrediction,
    SubmissionResponse,
    parse_catalog,
    parse_challenge,
    validate_indices,
)
from .errors import AssetDownloadError, ChallengeContractError, NetworkError, SubmissionError
from .security import assert_public_json

RETRY_STATUSES = {429, 502, 503, 504}
_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_IMAGE = re.compile(r"^[A-Za-z0-9_.-]+\.(?:webp|png|jpg|jpeg|gif)$", re.IGNORECASE)


class BenchmarkClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 60,
        max_retries: int = 2,
        http: httpx.Client | None = None,
        sleep=time.sleep,
    ):
        self.base_url = normalize_base_url(base_url)
        self.max_retries = max_retries
        self._sleep = sleep
        self._http = http or httpx.Client(timeout=timeout, follow_redirects=False)
        self._owns_http = http is None
        self._cache: dict[str, bytes] = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self) -> None:
        if self._owns_http:
            self._http.close()
        self._cache.clear()

    @staticmethod
    def _id(challenge_id: str) -> str:
        if not _ID.fullmatch(challenge_id):
            raise ChallengeContractError("Invalid public challenge identifier")
        return challenge_id

    def _url(self, reference: str, *, expected: str | None = None, asset_id=None) -> str:
        raw_path = urlsplit(reference).path
        if unquote(raw_path) != raw_path or any(
            segment in {".", ".."} for segment in raw_path.split("/")
        ):
            raise ChallengeContractError("Encoded or traversing resource path rejected")
        url = urljoin(self.base_url + "/", reference)
        parts = urlsplit(url)
        base = urlsplit(self.base_url)
        if (
            (parts.scheme, parts.hostname, parts.port) != (base.scheme, base.hostname, base.port)
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
            or "\\" in reference
        ):
            raise ChallengeContractError("Resource is outside the public benchmark origin")
        # Reject encoded/traversal paths, including repeated encoding, before any request.
        if unquote(parts.path) != parts.path or any(
            x in {".", ".."} for x in parts.path.split("/")
        ):
            raise ChallengeContractError("Encoded or traversing resource path rejected")
        if expected is not None and parts.path != expected:
            raise ChallengeContractError("Resource is outside the public path allowlist")
        if asset_id is not None:
            prefix = f"/challenges/{self._id(asset_id)}/assets/"
            filename = parts.path.removeprefix(prefix)
            if not parts.path.startswith(prefix) or not _IMAGE.fullmatch(filename):
                raise ChallengeContractError("Asset is outside the public image allowlist")
        return url

    @staticmethod
    def _inspect_json(response: httpx.Response) -> Any | None:
        # Inspect JSON even for error status codes and mislabelled asset responses.
        try:
            data = response.json()
        except (ValueError, UnicodeError):
            return None
        assert_public_json(data)
        return data

    def _request(self, method: str, url: str, *, payload=None) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = self._http.request(method, url, json=payload, follow_redirects=False)
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise NetworkError("Public benchmark transport failed") from None
            else:
                self._inspect_json(response)
                if response.status_code not in RETRY_STATUSES or attempt == self.max_retries:
                    return response
            self._sleep(min(0.5 * 2**attempt, 8))
        raise AssertionError("Unreachable retry state")

    def _get(self, url: str, *, asset: bool = False) -> bytes:
        if url in self._cache:
            return self._cache[url]
        try:
            response = self._request("GET", url)
        except NetworkError:
            if asset:
                raise AssetDownloadError("Public image transport failed") from None
            raise
        if response.status_code != 200:
            error_cls = AssetDownloadError if asset else NetworkError
            raise error_cls("Public resource HTTP failure", status_code=response.status_code)
        content_type = response.headers.get("content-type", "").split(";")[0].lower()
        if asset:
            if (
                not response.content
                or content_type
                not in {
                    "image/webp",
                    "image/png",
                    "image/jpeg",
                    "image/gif",
                }
                or self._inspect_json(response) is not None
            ):
                raise AssetDownloadError("Expected a nonempty public image response")
        self._cache[url] = response.content
        return response.content

    def _json(self, url: str) -> Any:
        try:
            data = json.loads(self._get(url))
        except (ValueError, UnicodeError):
            self._cache.pop(url, None)
            raise ChallengeContractError("Public resource is not valid JSON") from None
        assert_public_json(data)
        return data

    def get_catalog(self) -> list[CatalogEntry]:
        path = "/challenges/catalog.json"
        return parse_catalog(self._json(self._url(path, expected=path)))

    def get_challenge(self, entry: CatalogEntry | str) -> PublicChallenge:
        challenge_id = entry.id if isinstance(entry, CatalogEntry) else entry
        path = f"/challenges/{self._id(challenge_id)}/challenge.json"
        reference = entry.challengeUrl if isinstance(entry, CatalogEntry) else path
        challenge = parse_challenge(self._json(self._url(reference, expected=path)))
        if challenge.id != challenge_id:
            raise ChallengeContractError("Public challenge ID does not match requested ID")
        if isinstance(entry, CatalogEntry):
            if challenge.variant != entry.variant or challenge.level != entry.level:
                raise ChallengeContractError("Catalog and public challenge identity disagree")
        return challenge

    def download_assets(self, challenge: PublicChallenge) -> list[bytes]:
        # Validate the entire asset set before fetching any member.
        urls = [self._url(path, asset_id=challenge.id) for path in challenge.assets]
        return [self._get(url, asset=True) for url in urls]

    def submit(
        self,
        challenge: PublicChallenge,
        prediction: SolverPrediction,
    ) -> tuple[SubmissionResponse, int]:
        if prediction.challenge_id != challenge.id:
            raise SubmissionError("Prediction and public challenge IDs disagree")
        answer = prediction.answer
        if challenge.type == "image-selection":
            answer = validate_indices(answer, len(challenge.assets))
        path = f"/api/challenges/{self._id(challenge.id)}/submit"
        payload = {"answer": answer, "solveTimeMs": prediction.inference_time_ms}
        try:
            response = self._request("POST", self._url(path, expected=path), payload=payload)
        except NetworkError:
            raise SubmissionError("Submission transport failed") from None
        if response.status_code != 200:
            raise SubmissionError("Submission HTTP failure", status_code=response.status_code)
        try:
            result = SubmissionResponse.model_validate(response.json())
        except (ValueError, UnicodeError, ValidationError):
            raise SubmissionError("Invalid public submission response", status_code=200) from None
        if result.challengeId != challenge.id or result.variant != challenge.variant:
            raise SubmissionError("Submission response identity mismatch", status_code=200)
        return result, response.status_code
