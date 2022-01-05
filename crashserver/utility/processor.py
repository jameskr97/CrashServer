from dataclasses import dataclass


@dataclass
class DumpModule:
    base_address: str
    end_address: str
    code_id: str
    debug_file: str  # filename | empty string
    debug_id: str  # [[:xdigit:]]{33} | empty string
    filename: str
    version: str
    missing_symbols: bool

    @staticmethod
    def generate_list(json: dict):
        res = []

        for mod in json:
            res.append(
                DumpModule(
                    base_address=mod.get("base_addr"),
                    end_address=mod.get("end_addr"),
                    code_id=mod.get("code_id"),
                    debug_file=mod.get("debug_file"),
                    debug_id=mod.get("debug_id"),
                    filename=mod.get("filename"),
                    version=mod.get("version"),
                    # Default false, as the key won't be there if it's true
                    missing_symbols=mod.get("missing_symbols", False),
                )
            )
        return sorted(res, key=lambda x: x.debug_file.lower())


@dataclass
class SystemInfo:
    os_name: str = ""
    os_version: str = ""  # Linux | Windows NT | Mac OS X
    cpu_arch: str = ""  # x86 | amd64 | arm | ppc | sparc
    cpu_core_count: int = 0
    cpu_info: str = ""
    cpu_version_microcode: str = ""

    @staticmethod
    def generate(json: dict):
        return SystemInfo(
            os_name=json.get("os"),
            os_version=json.get("os_ver"),
            cpu_arch=json.get("cpu_arch"),
            cpu_info=json.get("cpu_info"),
            cpu_core_count=json.get("cpu_count"),
            cpu_version_microcode=json.get("cpu_microcode_version", ""),
        )


@dataclass
class CrashReason:
    crash_type: str
    crash_address: str
    crashing_thread: int
    assertion: str

    @staticmethod
    def generate(json: dict):
        return CrashReason(
            crash_type=json.get("type"),
            crash_address=json.get("address", "Unknown"),
            crashing_thread=json.get("crashing_thread"),
            assertion=json.get("assertion"),
        )


@dataclass
class ThreadFrame:
    frame_index: int
    file: str
    func: str
    func_offset: str
    line: int
    module: str
    module_offset: str
    offset: str
    registers: dict
    trust: str  # none | scan | cfi_scan | frame_pointer | cfi | context | prewalked

    @staticmethod
    def generate_list(frames: list):
        res = []
        for frame in frames:
            res.append(
                ThreadFrame(
                    frame_index=frame.get("frame"),
                    file=frame.get("file"),
                    func=frame.get("function"),
                    func_offset=frame.get("function_offset"),
                    line=frame.get("line"),
                    module=frame.get("module"),
                    module_offset=frame.get("module_offset"),
                    offset=frame.get("offset"),
                    registers={},
                    trust=frame.get("trust"),
                )
            )

        res.sort(key=lambda x: x.frame_index)
        return res


@dataclass
class StackThread:
    thread_index: int
    total_frames: int
    frames: [ThreadFrame]

    @staticmethod
    def generate_list(threads: list):
        res = []

        for i in range(len(threads)):
            res.append(
                StackThread(
                    thread_index=i,
                    total_frames=threads[i].get("frame_count"),
                    frames=ThreadFrame.generate_list(threads[i].get("frames")),
                )
            )

        res.sort(key=lambda x: x.thread_index)
        return res


@dataclass
class ProcessedCrash:
    crash_reason: CrashReason
    system: SystemInfo
    modules: [DumpModule]
    threads: [StackThread]

    main_module_index: int
    read_success: bool
    pid: int

    @property
    def modules_no_symbols(self) -> [DumpModule]:
        return [m for m in self.modules if m.missing_symbols]

    @property
    def main_module(self) -> DumpModule:
        return self.modules[self.main_module_index]

    @property
    def os_icon(self):
        if self.system.os_name == "Windows NT":
            return "fab fa-windows"
        if self.system.os_name == "Mac OS X":
            return "fab fa-apple"
        if self.system.os_name == "Linux":
            return "fab fa-linux"
        return ""

    @property
    def os_name(self):
        if self.system.os_name == "Windows NT":
            return "Windows"
        if self.system.os_name == "Mac OS X":
            return "macOS"
        if self.system.os_name == "Linux":
            return "Linux"
        return ""

    @staticmethod
    def generate(json: dict):
        res_reason = CrashReason.generate(json.get("crash_info"))
        res_threads = StackThread.generate_list(json.get("threads"))

        # Update first frame of crashing thread with registers.
        # The registers should always be in the first frame of the crashing thread
        crash_registers = json.get("crashing_thread").get("frames")[0]["registers"]
        res_threads[res_reason.crashing_thread].frames[0].registers = crash_registers

        return ProcessedCrash(
            read_success=True,
            crash_reason=res_reason,
            system=SystemInfo.generate(json.get("system_info", {})),
            modules=DumpModule.generate_list(json.get("modules", {})),
            threads=res_threads,
            main_module_index=json.get("main_module"),
            pid=json.get("pid"),
        )
