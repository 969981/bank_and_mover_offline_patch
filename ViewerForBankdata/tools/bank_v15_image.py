# -*- coding: utf-8 -*-
"""Immutable Pokemon Bank v1.5 current-image wrapper.

This module deliberately treats unknown fields as opaque bytes. The PKHeX
compatibility import path and Route A V0 apply path only replace the 100 main
Bank boxes. Header, Transfer Box, current-format metadata, counters and tail
remain owned by the runtime/current image.
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

    def apply_main_boxes_from(self, bulk: "BankV15Image") -> "BankV15Image":
        """Apply the Route A V0 whitelist to this runtime/current image.

        Only 0x17C..0xAAF14 is copied from ``bulk``. Every byte outside the
        100 main boxes is preserved from ``self``. This mirrors the intended
        3DS Offline Apply implementation.
        """
        if not isinstance(bulk, BankV15Image):
            raise TypeError("bulk must be a BankV15Image")
        merged = bytearray(self._data)
        merged[PKHEX_IMPORT_START:PKHEX_IMPORT_END] = bulk._data[
            PKHEX_IMPORT_START:PKHEX_IMPORT_END
        ]
        return type(self)(bytes(merged))
