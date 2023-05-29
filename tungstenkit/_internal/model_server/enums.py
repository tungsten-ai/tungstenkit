from enum import Enum


class ModelServerMode(str, Enum):
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    FILE_TUNNEL = "file_tunnel"
