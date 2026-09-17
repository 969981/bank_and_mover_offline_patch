# bankdata diagnostic tools

The Python files in this directory provide read-only format diagnostics used
by the GUI or by command-line investigation. Input files must be selected
explicitly; the tools do not search for bankdata or RomFS.

```powershell
python .\tools\parse_bank_file.py "D:\path\to\bankdata.bin"
python .\tools\list_bank_file.py --input "D:\path\to\bankdata.bin" --grid --range 0 3
python .\tools\find_species.py 698 --input "D:\path\to\bankdata.bin"
python .\tools\diff_bank_file.py "D:\before.bin" "D:\after.bin"
python .\tools\diff_bank_file.py "D:\before.bin" "D:\after.bin" --json "D:\diff.json"
```

`bank_v15_layout.py` defines the physical regions of the Bank v1.5 `0xBB518`
serialized body and the shared index formula for all 3000 Bank slots.
`diff_bank_file.py` groups Pokemon payload, format-tag, source-software, and
timestamp changes for the same slot, while reporting source summaries,
Pokedex-like aggregate data, counters, tail bytes, and other regions separately.

The tools report raw values and physical changes only. Business meanings for
tag/source/timestamp values remain research results rather than guessed labels.

## Route A full image and PKHeX compatibility view

`bankbulk.py` safely converts between a full `0xBB518` Bank v1.5 current image
and the legacy-sized `0xACA48` compatibility view understood by PKHeX `Bank7`.
The full current image always remains the authoritative template; the PKHeX
view is only for inspecting or editing the 100 main boxes.

Validate or inspect a full image:

```powershell
python .\tools\bankbulk.py validate "D:\Bank\bankdata.bin"
python .\tools\bankbulk.py inspect "D:\Bank\bankdata.bin"
```

Export a PKHeX-only compatibility view:

```powershell
python .\tools\bankbulk.py export-pkhex `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bankdata_pkhex_view.bin"
```

The result is exactly `0xACA48` / 707144 bytes.

After PKHeX edits and saves that view, merge it back into the original full
current image instead of using the `0xACA48` file directly:

```powershell
python .\tools\bankbulk.py import-pkhex `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\bankdata_pkhex_view_edited.bin" `
  -o "D:\Bank\bulk_import.bin"
```

The merge copies only `0x00017C..0x0AAF14` (end-exclusive), which is the 100
main Bank boxes including each box's `0x26` metadata. Header bytes, Transfer
Box data, the `0xACA44..0xACA47` legacy/current overlap, and all later current
metadata remain from the full template.

To validate and copy an already-complete current image directly to
`bulk_import.bin`:

```powershell
python .\tools\bankbulk.py build `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bulk_import.bin"
```

Run the tests with:

```powershell
python -m unittest discover -s .\tests -v
```

`text_resources.py` is the GUI's local-resource reader. It is not a RomFS
extractor. Descriptive field names document observed behavior and do not claim
to be original program symbols.
