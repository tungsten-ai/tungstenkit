import platform

from packaging.version import Version

py_version = Version(platform.python_version())
if py_version >= Version("3.8"):
    import importlib.metadata

    pkg_version = importlib.metadata.version(__package__ or __name__)

else:
    import pkg_resources

    pkg_version = pkg_resources.get_distribution(__package__ or __name__).version
