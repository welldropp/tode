"""ImageLoader + ImageFrameExtractor."""
import os

import cv2
import numpy as np

from core.image_frame_extractor import ImageFrameExtractor
from core.image_loader import ImageLoader


class TestImageLoader:
    def test_load_single_image(self, tmp_path):
        img_path = str(tmp_path / "test.png")
        cv2.imwrite(img_path, np.zeros((100, 100, 3), dtype=np.uint8))
        loader = ImageLoader(img_path)
        loader.open()
        assert loader.total_frames == 1
        assert loader.fps == 1.0

    def test_load_folder(self, tmp_path):
        for i in range(4):
            cv2.imwrite(
                str(tmp_path / f"img_{i:03d}.jpg"),
                np.zeros((50, 50, 3), dtype=np.uint8),
            )
        loader = ImageLoader(str(tmp_path))
        loader.open()
        assert loader.total_frames == 4

    def test_read_frame_returns_ndarray(self, tmp_path):
        img_path = str(tmp_path / "frame.png")
        cv2.imwrite(img_path, np.full((80, 60, 3), 128, dtype=np.uint8))
        loader = ImageLoader(img_path)
        loader.open()
        frame = loader.read_frame(0)
        assert frame is not None
        assert frame.shape == (80, 60, 3)

    def test_read_out_of_range_returns_none(self, tmp_path):
        img_path = str(tmp_path / "only.png")
        cv2.imwrite(img_path, np.zeros((10, 10, 3), dtype=np.uint8))
        loader = ImageLoader(img_path)
        loader.open()
        assert loader.read_frame(99) is None

    def test_is_open_after_open(self, tmp_path):
        img_path = str(tmp_path / "x.png")
        cv2.imwrite(img_path, np.zeros((10, 10, 3), dtype=np.uint8))
        loader = ImageLoader(img_path)
        assert not loader.is_open()
        loader.open()
        assert loader.is_open()


class TestImageFrameExtractor:
    def test_extracts_all_images(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        for i in range(3):
            cv2.imwrite(
                str(src_dir / f"img_{i}.png"),
                np.zeros((10, 10, 3), dtype=np.uint8),
            )

        loader = ImageLoader(str(src_dir))
        loader.open()

        extractor = ImageFrameExtractor(loader, str(out_dir))
        results = list(extractor.extract())
        assert len(results) == 3
        for _idx, frame, path in results:
            assert os.path.exists(path)
            # Fix 2: ImageFrameExtractor skips decode and yields None for frame
            assert frame is None
