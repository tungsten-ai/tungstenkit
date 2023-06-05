from tungstenkit.exceptions import TungstenException


class PredictionIDAlreadyExists(TungstenException):
    pass


class InputIDAlreadyExists(TungstenException):
    pass


class PredictionIDNotFound(TungstenException):
    pass


class InputIDNotFound(TungstenException):
    pass


class SetupFailed(TungstenException):
    pass


class PredictionCanceled(TungstenException):
    pass


class PredictionTimeout(TungstenException):
    pass


class SubprocessTerminated(TungstenException):
    pass
