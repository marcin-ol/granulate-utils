#
# Copyright (c) Granulate. All rights reserved.
# Licensed under the AGPL3 License. See LICENSE.md in the project root for license information.
#
import errno
import os
import time
from typing import Iterable, List, Tuple

from granulate_utils.linux.kernel_messages import KernelMessage, KernelMessagesProvider

# See linux/printk.h
CONSOLE_EXT_LOG_MAX = 8192


class DevKmsgProvider(KernelMessagesProvider):
    """
    Provides a stream of kernel messages via /dev/kmsg. Requires Linux 3.5+.

    The /dev/kmsg interface is described at Documentation/ABI/testing/dev-kmsg in the kernel source tree
    and can be viewed at https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/dev-kmsg.
    """

    def __init__(self):
        self.dev_kmsg = open("/dev/kmsg", "rb", buffering=0)
        os.set_blocking(self.dev_kmsg.fileno(), False)
        # skip all historical messages:
        os.lseek(self.dev_kmsg.fileno(), 0, os.SEEK_END)

    def iter_new_messages(self) -> Iterable[KernelMessage]:
        messages: List[Tuple[float, bytes]] = []
        try:
            # Each read() is one message
            while True:
                try:
                    message = os.read(self.dev_kmsg.fileno(), CONSOLE_EXT_LOG_MAX)
                    messages.append((time.time(), message))
                except BrokenPipeError:
                    self.on_missed()
        except OSError as e:
            if e.errno != errno.EAGAIN:
                raise

        yield from self._parse_raw_messages(messages)

    @staticmethod
    def _parse_raw_messages(messages: List[Tuple[float, bytes]]) -> Iterable[KernelMessage]:
        for timestamp, message in messages:
            """
            Example messages:
            7,492,1207557,-;ahci 0000:00:0d.0: version 3.0\n SUBSYSTEM=pci\n DEVICE=+pci:0000:00:0d.0
            6,339,5140900,-;NET: Registered protocol family 10
            30,340,5690716,-;udevd[80]: starting version 181
            """
            prefix, text = message.decode().split(";", maxsplit=1)
            fields = prefix.split(",")
            level = int(fields[0])
            yield timestamp, level, text
