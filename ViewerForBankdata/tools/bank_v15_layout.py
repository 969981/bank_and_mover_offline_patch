# -*- coding: utf-8 -*-
"""Physical layout helpers for Pokemon Bank v1.5 serialized BankObject bodies.

All offsets are relative to the first byte of the serialized file body, not the
8-byte runtime object header.  This module intentionally names only fields whose
physical location is established; unknown business semantics remain opaque.
"""

from dataclasses import dataclass
import struct
from typing import Sequence

CURRENT_SIZE = 0xBB518
LEGACY_SIZE = 0xACA48

VERSION_OFFSET = 0x15C
BOX_COUNT_OFFSET = 0x15E
CURRENT_VERSION = 2
BANK_BOX_COUNT = 100
SLOTS_PER_BOX = 30
SLOT_COUNT = BANK_BOX_COUNT * SLOTS_PER_BOX
POKEMON_SIZE = 0xE8
BOX_STRIDE = 0x1B56
BOX_POKEMON_BYTES = SLOTS_PER_BOX * POKEMON_SIZE  # 0x1B30
BOX_METADATA_SIZE = BOX_STRIDE - BOX_POKEMON_BYTES  # 0x26

HEADER_START = 0x000000
BANK_BOXES_START = 0x00017C
TRANSFER_BOX_START = 0x0AAF14
BANK_TAGS_START = 0x0ACA44
TRANSFER_TAGS_START = 0x0AD5FC
ALIGNMENT_START = 0x0AD61A
SOURCE_SUMMARIES_START = 0x0AD61C
POKEDEX_AGGREGATE_START = 0x0AD83C
COUNTERS_START = 0x0B4A9C
SOURCE_SOFTWARE_START = 0x0B4AA0
TIMESTAMPS_START = 0x0B5658
TAIL_START = 0x0BB418

# BankFile_LoadLegacyBody initializes a current object, then copies the entire
# 0xACA48 legacy body over its prefix.  Since current bank tags begin at
# 0xACA44, the legacy copy overlaps the first four bytes of that current table.
LEGACY_OVERLAP_START = BANK_TAGS_START
LEGACY_OVERLAP_END = LEGACY_SIZE
LEGACY_OVERLAP_SIZE = LEGACY_OVERLAP_END - LEGACY_OVERLAP_START
CURRENT_ONLY_START = LEGACY_SIZE


@dataclass(frozen=True)
class Region:
    name: str
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start


REGIONS = (
    Region("header", HEADER_START, BANK_BOXES_START),
    Region("bank_boxes", BANK_BOXES_START, TRANSFER_BOX_START),
    Region("transfer_box", TRANSFER_BOX_START, BANK_TAGS_START),
    Region("bank_tags", BANK_TAGS_START, TRANSFER_TAGS_START),
    Region("transfer_tags", TRANSFER_TAGS_START, ALIGNMENT_START),
    Region("alignment", ALIGNMENT_START, SOURCE_SUMMARIES_START),
    Region("source_summaries", SOURCE_SUMMARIES_START, POKEDEX_AGGREGATE_START),
    Region("pokedex_aggregate", POKEDEX_AGGREGATE_START, COUNTERS_START),
    Region("counters", COUNTERS_START, SOURCE_SOFTWARE_START),
    Region("source_software", SOURCE_SOFTWARE_START, TIMESTAMPS_START),
    Region("timestamps", TIMESTAMPS_START, TAIL_START),
    Region("tail", TAIL_START, CURRENT_SIZE),
)


@dataclass(frozen=True)
class SlotOffsets:
    index: int
    box: int
    slot: int
    pokemon: int
    tag: int
    source_software: int
    timestamp: int


def slot_index(box: int, slot: int) -> int:
    if not 0 <= box < BANK_BOX_COUNT:
        raise ValueError(f"box out of range: {box}; expected 0..{BANK_BOX_COUNT - 1}")
    if not 0 <= slot < SLOTS_PER_BOX:
        raise ValueError(f"slot out of range: {slot}; expected 0..{SLOTS_PER_BOX - 1}")
    return box * SLOTS_PER_BOX + slot


def slot_offsets(box: int, slot: int) -> SlotOffsets:
    index = slot_index(box, slot)
    pokemon = BANK_BOXES_START + box * BOX_STRIDE + slot * POKEMON_SIZE
    return SlotOffsets(
        index=index,
        box=box,
        slot=slot,
        pokemon=pokemon,
        tag=BANK_TAGS_START + index,
        source_software=SOURCE_SOFTWARE_START + index,
        timestamp=TIMESTAMPS_START + index * 8,
    )


def region_for_offset(offset: int) -> str:
    if not 0 <= offset < CURRENT_SIZE:
        raise ValueError(f"offset out of range: 0x{offset:X}")
    if BANK_BOXES_START <= offset < TRANSFER_BOX_START:
        rel = offset - BANK_BOXES_START
        within_box = rel % BOX_STRIDE
        return "bank_slot_payload" if within_box < BOX_POKEMON_BYTES else "box_metadata"
    for region in REGIONS:
        if region.start <= offset < region.end:
            return region.name
    raise AssertionError(f"unmapped offset: 0x{offset:X}")


def validate_current(data: Sequence[int]) -> list[str]:
    errors: list[str] = []
    if len(data) != CURRENT_SIZE:
        return [f"size mismatch: got 0x{len(data):X}, expected 0x{CURRENT_SIZE:X}"]
    version = struct.unpack_from("<H", data, VERSION_OFFSET)[0]
    box_count = struct.unpack_from("<H", data, BOX_COUNT_OFFSET)[0]
    if version != CURRENT_VERSION:
        errors.append(f"version mismatch: got {version}, expected {CURRENT_VERSION}")
    if box_count != BANK_BOX_COUNT:
        errors.append(f"box count mismatch: got {box_count}, expected {BANK_BOX_COUNT}")
    return errors
