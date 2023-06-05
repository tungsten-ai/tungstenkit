from enum import IntEnum


class Application(IntEnum):
    CLI = 0
    MODEL_SERVER = 1
    TASK_SERVER = 2


APP = Application.CLI
