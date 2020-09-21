import pkg_resources


try:
    __version__ = pkg_resources.require('connect-cli')[0].version
except:  # pragma: no cover noqa: E722
    __version__ = '0.0.1'


def get_version():
    return __version__
