from typing import Optional


class TungstenException(Exception):
    """
    Base class for all Tungstenkit's errors.
    Each custom exception should be derived from this class.
    """

    pass


# TODO group exceptions


class TungstenModelError(TungstenException):
    pass


class DockerError(TungstenException):
    pass


class NotLoggedIn(TungstenException):
    pass


class InvalidName(TungstenException):
    pass


class InvalidURL(TungstenException):
    pass


class NotFound(TungstenException):
    pass


class ModelImageNotFound(TungstenException):
    pass


class ModelConfigError(TungstenException):
    pass


class TungstenTaskError(TungstenException):
    pass


class ClientError(TungstenException):
    def __init__(
        self,
        url: str,
        status_code: int,
        reason: str,
        detail: str,
        msg_prefix: Optional[str] = None,
    ):
        self.url = url
        self.status_code = status_code
        self.reason = reason
        self.detail = detail
        self.msg_prefix = msg_prefix

    def __str__(self):
        basic_err_msg = f"{self.url} - Response {self.status_code} {self.reason}"
        if self.msg_prefix:
            err_msg = f"{self.msg_prefix} ({basic_err_msg})"
        else:
            err_msg = "Request failed to " + basic_err_msg
        err_msg += f"\n\nDetails:\n{self.detail}"
        return err_msg


class TungstenClientError(ClientError):
    pass


class ModelClientError(ClientError):
    pass


class DownloadError(TungstenException):
    pass


class UploadError(TungstenException):
    pass


class Conflict(TungstenException):
    pass


class BuildError(TungstenException):
    pass


class InvalidOutput(TungstenException):
    pass


class InvalidDemoOutput(TungstenException):
    pass


class PipPackageParseError(TungstenException):
    pass


class NoCompatibleVersion(TungstenException):
    pass


class NoCompatiblePythonPackage(TungstenException):
    pass


class NoCompatiblePythonVersion(TungstenException):
    pass


class NoCompatibleCUDAImage(TungstenException):
    pass


class NoCompatiblePythonImage(TungstenException):
    pass


class PythonPackageMetadataError(TungstenException):
    pass


class UnsupportedURL(TungstenException):
    pass


class StoredDataError(TungstenException):
    pass


class InvalidInput(TungstenException):
    pass


class PredictionFailure(TungstenException):
    pass
