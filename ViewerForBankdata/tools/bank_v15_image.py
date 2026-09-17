# -*- coding: utf-8 -*-
"""Immutable Pokemon Bank v1.5 current-image wrapper.

This module deliberately treats unknown fields as opaque bytes.  The PKHeX
compatibility import path only replaces the 100 main Bank boxes and leaves
header, Transfer Box, current-format tag overlap, and later metadata untouched.
"""

from dataclasses import dataclass

import bank_v15_layout as layout

PKHEX_VIEW_SIZE = layout.LEGACY_SIZE
PKHEX_IMPORT_START = layout.BANK_BOXES_START
PKHEX_IMPORT_END = layout.TRANSFER_BOX_START


@dataclass(frozen=True)
class BankV15Image:
    _data: bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> "BankV15Image":
        raw = bytes(data)
        errors = layout.validate_current(raw)
        if errors:
            raise ValueError("; ".join(errors))
        return cls(raw)

    def to_bytes(self) -> bytes:
        return self._data

    def main_box_bytes(self) -> bytes:
        return self._data[PKHEX_IMPORT_START:PKHEX_IMPORT_END]

    def export_pkhex_view(self) -> bytes:
        return self._data[:PKHEX_VIEW_SIZE]

    def import_pkhex_view(self, view: bytes) -> "BankV15Image":
        view = bytes(view)
        if len(view) != PKHEX_VIEW_SIZE:
            raise ValueError(
                f"PKHeX view size mismatch: got 0x{len(view):X}, expected 0x{PKHEX_VIEW_SIZE:X}"
            )
        merged = bytearray(self._data)
        merged[PKHEX_IMPORT_START:PKHEX_IMPORT_END] = view[PKHEX_IMPORT_START:PKHEX_IMPORT_END]
        return type(self)(bytes(merged))
