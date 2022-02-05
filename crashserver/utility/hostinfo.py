import socket
import sys


class HostInfo:
    @staticmethod
    def get_hostname() -> str:
        return socket.gethostname()

    @staticmethod
    def get_python_version():
        info = sys.version_info
        return "Python {}.{}.{}".format(info.major, info.minor, info.micro)
