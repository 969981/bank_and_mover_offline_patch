# Viewer for bankdata

This directory contains a read-only, standard-library Python viewer and small
diagnostic tools for local bankdata files. The GUI includes fixed text
resources for all ten supported language selections and does not require an
extracted RomFS at runtime.

```powershell
cd ViewerForBankdata
python .\gui\bank_viewer.py
```

The viewer opens without a preset input. Select the bankdata file through the
file dialog. See `gui/README.md` for GUI options and `tools/README.md` for the
command-line diagnostics.
