import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from loguru import logger
from pathlib import Path
from typing import Tuple

import typer
from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

app = typer.Typer()


class GlobalConfig:
    def __init__(self, path_to_work_on: str):
        self.path_to_work_on = path_to_work_on
        Path(self.path_to_work_on).mkdir(parents=True, exist_ok=True)


class VideoConverter:
    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config

    def convert(self, filepath_for_source_video: str, ext_of_video: str):
        source_path = Path(filepath_for_source_video)
        logger.info(f"convert request {source_path}")

        if not source_path.is_file():
            logger.warning(f"skip convert; not a file: {source_path}")
            return

        if not self._wait_for_stable_file(source_path):
            logger.warning(f"skip convert; file did not stabilize: {source_path}")
            return

        (filepath_for_video, filepath_for_image) = self._get_paths(source_path, ext_of_video)
        try:
            self._move_video_to_work_on(str(source_path), filepath_for_video)
            self._convert_video_to_image(filepath_for_video, filepath_for_image)
        except Exception:
            logger.exception(f"conversion failed for {source_path}")

    def _wait_for_stable_file(self, path: Path, checks: int = 3, delay_seconds: float = 0.2) -> bool:
        last_size = -1
        for _ in range(checks):
            current_size = path.stat().st_size
            if current_size == last_size:
                return True
            last_size = current_size
            time.sleep(delay_seconds)
        return False

    def _get_paths(self, filepath_for_source_video: Path, ext_of_video: str) -> Tuple[str, str]:
        path_to_work_on = self.global_config.path_to_work_on
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        FLAG_PRESERVE_BASE = False
        if FLAG_PRESERVE_BASE:
            # Replace any character that is not a letter, number, underscore, or hyphen with a hyphen
            base = re.sub(r"[^A-Za-z0-9_-]", "-", filepath_for_source_video.stem) or "video"
        else:
            base = "video"
        filename_for_video = f"{base}-{timestamp}-{filepath_for_source_video.stat().st_mtime_ns}.{ext_of_video}"
        filename_for_image = f"{base}-{timestamp}-{filepath_for_source_video.stat().st_mtime_ns}-last-frame.png"

        filepath_for_video = os.path.join(path_to_work_on,  filename_for_video)
        filepath_for_image = os.path.join(path_to_work_on,  filename_for_image)

        return (filepath_for_video, filepath_for_image)

    def _move_video_to_work_on(self, filepath_for_source_video: str, filepath_for_video: str):
        shutil.move(filepath_for_source_video, filepath_for_video)

    def _convert_video_to_image(self, filepath_for_video: str, filepath_for_image: str):
        self._run_command([
            "ffmpeg",
            "-sseof", "-1",
            "-i", filepath_for_video,
            "-update", "1",
            "-q:v", "1",
            filepath_for_image
        ])

    def _run_command(self, cmd: list[str]):
        logger.info("+ {}", " ".join(cmd))
        subprocess.run(cmd, check=True)


class CustomFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, pattern_to_watch: str, ext_of_video: str, video_converter: VideoConverter):
        """
        Initialize the event handler.

        Args:
            pattern_to_watch (str): The pattern to watch for file changes.
            ext_of_video (str): The extension of the video files to convert.
            video_converter (VideoConverter): The video converter instance.
        """
        self.pattern_to_watch = pattern_to_watch
        self.ext_of_video = ext_of_video
        self.video_converter = video_converter

    def on_created(self, event):
        logger.info(f"on_created {event.src_path}")

    def on_modified(self, event):
        if event.is_directory:
            return
        logger.info(f"on_modified {event.src_path}")
        match_result = re.match(self.pattern_to_watch, event.src_path)
        if match_result:
            try:
                self.video_converter.convert(event.src_path, self.ext_of_video)
            except Exception:
                logger.exception(f"conversion crashed for {event.src_path}")


@app.command()
def watch(path_to_work_on: str, path_to_watch: str, pattern_to_watch: str, ext_of_video: str):
    logger.info(f"watching {path_to_watch} for pattern {pattern_to_watch}. Ext is {ext_of_video}. Files stored in {path_to_work_on}")
    global_config = GlobalConfig(path_to_work_on)

    video_converter = VideoConverter(global_config)
    path = path_to_watch
    event_handler = CustomFileSystemEventHandler(pattern_to_watch, ext_of_video, video_converter)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    app()
