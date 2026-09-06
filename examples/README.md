# Examples

Self-contained scripts that exercise the headless layers of `tode`. None
of them require Tk, a display, or a webcam.

| Script                       | What it shows                                                    |
|------------------------------|------------------------------------------------------------------|
| `onnx_inference.py`          | Loading an `.onnx` model and running detection on a single image |
| `export_dataset.py`          | Building annotations in code and exporting as YOLO + COCO        |

Run from the repository root, e.g.:

```bash
python examples/export_dataset.py /tmp/tode_export_demo
```

These scripts also serve as integration smoke tests — if they fail, the
production code path is broken regardless of what the unit tests report.
