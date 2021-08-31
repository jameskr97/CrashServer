import pathlib
import shutil
import os


def get_directory_size(start_path):
    """
    Traverse through all directories and folders within a path, and sum all the file size,
    within that path
    :param start_path: The path to search through
    :return: The file size in bytes
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size


def get_disk_space(path):
    return shutil.disk_usage(path)


def get_filename_from_path(path):
    if path:
        path = path.replace("\\", "/")
        return pathlib.Path(path).name
    return None
