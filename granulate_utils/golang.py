#
# Copyright (c) Granulate. All rights reserved.
# Licensed under the AGPL3 License. See LICENSE.md in the project root for license information.
#

import functools
import struct
from typing import Optional

from psutil import NoSuchProcess, Process

from granulate_utils.linux.elf import get_elf_buildid, read_elf_symbol, read_elf_va
from granulate_utils.linux.process import is_kernel_thread


def is_golang_process(process: Process) -> bool:
    return not is_kernel_thread(process) and get_golang_buildid(process) is not None


@functools.lru_cache(maxsize=4096)
def get_golang_buildid(process: Process) -> Optional[str]:
    """
    Gets the golang build ID embedded in an ELF file section as a string, or None if not present.
    """
    elf_path = f"/proc/{process.pid}/exe"
    try:
        # section .note.go.buildid has been added since version 1.5: https://github.com/golang/go/issues/11048
        golang_buildid = get_elf_buildid(elf_path, ".note.go.buildid", lambda note: note.n_name == "Go")
        return golang_buildid
    except FileNotFoundError:
        raise NoSuchProcess(process.pid)


@functools.lru_cache(maxsize=4096)
def get_process_golang_version(process: Process) -> Optional[str]:
    elf_path = f"/proc/{process.pid}/exe"
    try:
        symbol_data = read_elf_symbol(elf_path, "runtime.buildVersion", 16)
    except FileNotFoundError:
        raise NoSuchProcess(process.pid)
    if symbol_data is None:
        return None

    # Declaration of go string type:
    # type stringStruct struct {
    # 	str unsafe.Pointer
    # 	len int
    # }
    addr, length = struct.unpack("QQ", symbol_data)
    try:
        golang_version_bytes = read_elf_va(elf_path, addr, length)
    except FileNotFoundError:
        raise NoSuchProcess(process.pid)
    if golang_version_bytes is None:
        return None

    return golang_version_bytes.decode()
