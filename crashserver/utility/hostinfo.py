import socket
import sys
import os


class HostInfo:
    @staticmethod
    def is_inside_docker() -> bool:
        return bool(os.environ.get("DOCKER", False))

    @staticmethod
    def get_hostname() -> str:
        return socket.gethostname()

    @staticmethod
    def get_python_version():
        info = sys.version_info
        return "Python {}.{}.{}".format(info.major, info.minor, info.micro)
