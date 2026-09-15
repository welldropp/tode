# Packaging tode as an installable desktop app

tode ships as a **WEKA-style installer**: a self-contained bundle (its own Python
runtime + PySide6 + torch/transformers/supervision) wrapped in a setup wizard.
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

## Customized installer

`tode_installer.iss` is a branded, modern-wizard setup:

- **Branding** — `tode.ico` (setup icon, shortcuts, Add/Remove Programs) and
  `wizard-large.bmp` / `wizard-small.bmp` (wizard artwork).
- **License page** — shows `LICENSE` (MIT) during install.
- **Publisher / URLs** — welldropp + GitHub links; full version metadata on the
  `.exe`.
- **Tasks** — optional desktop + quick-launch shortcuts.
- **Registry** — records install dir + version under `HKCU\Software\welldropp\tode`.
- **Clean uninstall** — removes the app's `logs/` on uninstall (leaves datasets).

Regenerate the branding assets with `python packaging/make_assets.py`. To embed
the icon in `tode.exe` itself, rebuild with PyInstaller (`tode.spec` references
`packaging/tode.ico`).

## Files

- `tode.spec` — PyInstaller build spec (bundles the app + all deps)
- `tode_installer.iss` — Inno Setup script (branded Windows setup wizard)
- `tode.ico`, `wizard-large.bmp`, `wizard-small.bmp` — installer branding
- `make_assets.py` — regenerates the branding assets (Pillow)
- `build_linux.sh` / `build_windows.ps1` — one-command local builds
