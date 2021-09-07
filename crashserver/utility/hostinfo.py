import socket
import os


class HostInfo:
    @staticmethod
    def is_inside_docker() -> bool:
        return bool(os.environ.get("DOCKER", False))

    @staticmethod
    def get_hostname() -> str:
        return socket.gethostname()
