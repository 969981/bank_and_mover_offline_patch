# bankdata diagnostic tools

The Python files in this directory provide read-only format diagnostics used
by the GUI or by command-line investigation. Input files must be selected
explicitly; the tools do not search for bankdata or RomFS.

```powershell
python .\tools\parse_bank_file.py "D:\path\to\bankdata.bin"
python .\tools\list_bank_file.py --input "D:\path\to\bankdata.bin" --grid --range 0 3
python .\tools\find_species.py 698 --input "D:\path\to\bankdata.bin"
```

`text_resources.py` is the GUI's local-resource reader. It is not a RomFS
extractor. Descriptive field names document observed behavior and do not claim
to be original program symbols.
