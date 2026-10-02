"""Typed failures with safe, non-payload error messages."""


class SolverError(Exception):
    status_code: int | None = None

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class NetworkError(SolverError):
    pass


class ChallengeContractError(SolverError):
    pass


class AssetDownloadError(SolverError):
    pass


class ModelError(SolverError):
    provider_error_code: str | None = None
    inference_time_ms: float | None = None
    api_request_count: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None


class ModelResponseError(ModelError):
    pass


class SubmissionError(SolverError):
    pass


class PublicDataLeakError(SolverError):
    """Fatal to the entire run, including leaks on otherwise failed requests."""

    def __init__(self):
        super().__init__("PUBLIC DATA LEAK DETECTED")
