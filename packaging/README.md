# Packaging tode as an installable desktop app

tode ships as a **WEKA-style installer**: a self-contained bundle (its own Python
runtime + PyQt6 + torch/transformers/supervision) wrapped in a setup wizard.
RT-DETR model weights are **not** bundled — they download from the HuggingFace
Hub on first use.

## What builds where

| Target | Tool chain | Output |
|--------|-----------|--------|
| Windows | PyInstaller → Inno Setup | `packaging/Output/tode-setup.exe` (install wizard) |
| Linux   | PyInstaller → tar | `dist/tode-linux-x86_64.tar.gz` |

> A Windows `.exe` can only be built on Windows (PyInstaller does not
> cross-compile). Use the **Build installers** GitHub Actions workflow — it runs
> a Windows runner for the `.exe` and an Ubuntu runner for the Linux bundle —
> or build locally on each OS with the scripts below.

## Local builds

```bash
# Linux
bash packaging/build_linux.sh

# Windows (PowerShell); install Inno Setup first: https://jrsoftware.org/isdl.php
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

## CI

Trigger **Actions → Build installers → Run workflow**, or push a `v*` tag. Both
artifacts are uploaded to the run.

## Files

- `tode.spec` — PyInstaller build spec (bundles the app + all deps)
- `tode_installer.iss` — Inno Setup script (the Windows setup wizard)
- `build_linux.sh` / `build_windows.ps1` — one-command local builds
