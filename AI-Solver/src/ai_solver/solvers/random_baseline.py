import hashlib
import random
import time

from ..contracts import PublicChallenge, SolverPrediction, validate_street_grid


class RandomBaseline:
    name = "random-independent-tiles"
    model_name = "bernoulli"

    def __init__(self, *, seed: int = 42, probability: float = 0.33):
        if not 0 <= probability <= 1:
            raise ValueError("Random selection probability must be between zero and one")
        self.seed = seed
        self.probability = probability

    def solve(self, challenge: PublicChallenge, assets: list[bytes]) -> SolverPrediction:
        start = time.perf_counter()
        validate_street_grid(challenge, assets)
        # Stable across process/platform, catalog order, limits, and preceding failures.
        digest = hashlib.sha256(f"{self.seed}:{challenge.id}".encode()).digest()
        rng = random.Random(int.from_bytes(digest, "big"))
        answer = [i for i in range(len(assets)) if rng.random() < self.probability]
        return SolverPrediction(
            challenge_id=challenge.id,
            answer=answer,
            solver_name=self.name,
            model_name=self.model_name,
            inference_time_ms=(time.perf_counter() - start) * 1000,
        )
