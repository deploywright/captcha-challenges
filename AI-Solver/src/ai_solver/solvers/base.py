from dataclasses import dataclass
from typing import Protocol

from ..contracts import PublicChallenge, SolverPrediction


class Solver(Protocol):
    name: str
    model_name: str

    def solve(self, challenge: PublicChallenge, assets: list[bytes]) -> SolverPrediction: ...


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    api_request_count: int = 1


class VisionProvider(Protocol):
    model_name: str

    def infer(self, instruction: str, assets: list[bytes], *, recovery: bool) -> ProviderResponse:
        """Receives only the public instruction and image bytes, never benchmark feedback."""
        ...
