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

Run the tests with:

```powershell
python -m unittest discover -s .\tests -v
```

`text_resources.py` is the GUI's local-resource reader. It is not a RomFS
extractor. Descriptive field names document observed behavior and do not claim
to be original program symbols.
