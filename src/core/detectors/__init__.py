"""
core/detectors/
────────────────
Detection backend implementations.

  RTDetrDetector — RT-DETR via HuggingFace transformers + supervision (Apache-2.0)

Heavy deps (torch / transformers / supervision) are imported lazily inside the
backend, so importing this package stays cheap. Import directly:

    from core.detectors.rtdetr_detector import RTDetrDetector
"""
