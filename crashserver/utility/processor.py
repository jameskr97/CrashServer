from dataclasses import dataclass


@dataclass
class CrashMetadata:
    # pylint: disable=too-many-instance-attributes
    """
    Data from the machine readable minidump to get additional info, and determine if we can decode the dump
    """
    # OS Line
    os_platform: str = ""
    os_version: str = ""

    # CPU Line
    cpu_arch: str = ""
    cpu_version: str = ""
    cpu_core_count: int = 0

    # Crash line
    crash_reason: str = ""
    crash_address: str = ""

    # Module line ending in "|1"
    module_id: str = ""
    build_id: str = ""


def process_machine_minidump(machine_text):
    """
    Processes `minidump_stackwalk` command run with the `-m` parameter.
    :param machine_text: The stdout output from the `minidump_stackwalk` command.
    :return: CrashMetadata object with all processed data
    """
    res = CrashMetadata()

    for line in machine_text:
        line = line.strip()
        split_data = line.split("|")
        if line.startswith("OS"):
            res.os_platform = split_data[1]
            res.os_version = split_data[2]

        elif line.startswith("CPU"):
            res.cpu_arch = split_data[1]
            res.cpu_version = split_data[2]
            res.cpu_core_count = int(split_data[3])

        elif line.startswith("Crash"):
            res.crash_reason = split_data[1]
            res.crash_address = split_data[2]

        elif not res.module_id and line.startswith("Module") and line.endswith("1"):
            res.module_id = split_data[3]
            res.build_id = split_data[4]

    return res
