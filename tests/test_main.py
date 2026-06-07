import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from main import CustomFileSystemEventHandler, GlobalConfig, VideoConverter


class VideoConverterTests(unittest.TestCase):
    def test_get_paths_sanitizes_name_and_uses_expected_suffixes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "bad file@name!.mp4"
            source_path.write_bytes(b"video")
            converter = VideoConverter(GlobalConfig(tmpdir))

            with patch("main.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20260607-123456"
                video_path, image_path = converter._get_paths(source_path, "mp4")

            expected_suffix = f"bad-file-name--20260607-123456-{source_path.stat().st_mtime_ns}"
            self.assertTrue(video_path.endswith(f"{expected_suffix}.mp4"))
            self.assertTrue(image_path.endswith(f"{expected_suffix}-last-frame.png"))
            self.assertTrue(video_path.startswith(tmpdir))
            self.assertTrue(image_path.startswith(tmpdir))

    def test_wait_for_stable_file_returns_true_when_size_stops_changing(self):
        converter = VideoConverter(GlobalConfig(tempfile.gettempdir()))
        path = MagicMock()
        path.stat.side_effect = [
            SimpleNamespace(st_size=10),
            SimpleNamespace(st_size=10),
        ]

        with patch("main.time.sleep") as mock_sleep:
            result = converter._wait_for_stable_file(path, checks=2, delay_seconds=0.01)

        self.assertTrue(result)
        self.assertEqual(mock_sleep.call_count, 1)

    def test_wait_for_stable_file_returns_false_when_size_keeps_changing(self):
        converter = VideoConverter(GlobalConfig(tempfile.gettempdir()))
        path = MagicMock()
        path.stat.side_effect = [
            SimpleNamespace(st_size=10),
            SimpleNamespace(st_size=11),
            SimpleNamespace(st_size=12),
        ]

        with patch("main.time.sleep"):
            result = converter._wait_for_stable_file(path, checks=3, delay_seconds=0.01)

        self.assertFalse(result)

    def test_convert_skips_missing_source_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            converter = VideoConverter(GlobalConfig(tmpdir))
            missing_path = str(Path(tmpdir) / "missing.mp4")

            with patch.object(converter, "_wait_for_stable_file") as mock_wait, patch.object(
                converter, "_move_video_to_work_on"
            ) as mock_move, patch.object(converter, "_convert_video_to_image") as mock_convert:
                converter.convert(missing_path, "mp4")

            mock_wait.assert_not_called()
            mock_move.assert_not_called()
            mock_convert.assert_not_called()

    def test_convert_skips_unstable_source_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source.mp4"
            source_path.write_bytes(b"video")
            converter = VideoConverter(GlobalConfig(tmpdir))

            with patch.object(converter, "_wait_for_stable_file", return_value=False) as mock_wait, patch.object(
                converter, "_move_video_to_work_on"
            ) as mock_move, patch.object(converter, "_convert_video_to_image") as mock_convert:
                converter.convert(str(source_path), "mp4")

            mock_wait.assert_called_once()
            mock_move.assert_not_called()
            mock_convert.assert_not_called()

    def test_convert_moves_and_converts_stable_source_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source.mp4"
            source_path.write_bytes(b"video")
            converter = VideoConverter(GlobalConfig(tmpdir))

            with patch.object(converter, "_wait_for_stable_file", return_value=True), patch.object(
                converter, "_get_paths", return_value=(f"{tmpdir}/out.mp4", f"{tmpdir}/out.png")
            ) as mock_get_paths, patch.object(converter, "_move_video_to_work_on") as mock_move, patch.object(
                converter, "_convert_video_to_image"
            ) as mock_convert:
                converter.convert(str(source_path), "mp4")

            mock_get_paths.assert_called_once_with(source_path, "mp4")
            mock_move.assert_called_once_with(str(source_path), f"{tmpdir}/out.mp4")
            mock_convert.assert_called_once_with(f"{tmpdir}/out.mp4", f"{tmpdir}/out.png")


class CustomFileSystemEventHandlerTests(unittest.TestCase):
    def test_on_modified_ignores_directories(self):
        converter = MagicMock()
        handler = CustomFileSystemEventHandler(r".*\.mp4$", "mp4", converter)
        event = SimpleNamespace(is_directory=True, src_path="/tmp/video.mp4")

        handler.on_modified(event)

        converter.convert.assert_not_called()

    def test_on_modified_ignores_non_matching_paths(self):
        converter = MagicMock()
        handler = CustomFileSystemEventHandler(r".*\.mp4$", "mp4", converter)
        event = SimpleNamespace(is_directory=False, src_path="/tmp/video.txt")

        handler.on_modified(event)

        converter.convert.assert_not_called()

    def test_on_modified_converts_matching_paths(self):
        converter = MagicMock()
        handler = CustomFileSystemEventHandler(r".*\.mp4$", "mp4", converter)
        event = SimpleNamespace(is_directory=False, src_path="/tmp/video.mp4")

        handler.on_modified(event)

        converter.convert.assert_called_once_with("/tmp/video.mp4", "mp4")


if __name__ == "__main__":
    unittest.main()
