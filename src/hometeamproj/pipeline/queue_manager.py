# pipeline/queue_manager.py
"""
Queue management for inter-process communication.
"""

import multiprocessing
from dataclasses import dataclass
from typing import Any
import importlib.util
from pathlib import Path

path = Path("/Users/bakr/Desktop/HoemTeam Project /HOMETEAMPROJ/src/hometeamproj/config.py")

spec = importlib.util.spec_from_file_location("config", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PipelineConfig = module.PipelineConfig


@dataclass
class FrameData:
    """Frame data structure passed through queues."""

    frame_id: int
    frame: Any  # numpy array
    timestamp: float


@dataclass
class DetectionData:
    """Detection data structure."""

    frame_id: int
    frame: Any
    motion_boxes: list  # List of (x, y, w, h) bounding boxes


@dataclass
class ViewportData:
    """Viewport data structure."""

    frame_id: int
    frame: Any
    viewport_center: tuple  # (x, y) center coordinates
    viewport_size: tuple  # (width, height)


class QueueManager:
    """Manages all queues for the pipeline."""

    def __init__(self, config: PipelineConfig):
        """
        Initialize queues.

        TODO: Create multiprocessing queues with appropriate maxsize.
        Consider using multiprocessing.Queue or multiprocessing.Manager().Queue()
        Use config.queue_max_size for the maxsize parameter to prevent unbounded memory growth.
        """
        self.config = config
        #NOTE: here in my implementation i will be using multiprocessing.Queue for faste execution
        # TODO: Initialize queues

        # self.raw_frames_queue = multiprocessing.Queue(maxsize=config.queue_max_size)
        # self.detections_queue = multiprocessing.Queue(maxsize=config.queue_max_size)
        # self.viewport_queue = multiprocessing.Queue(maxsize=config.queue_max_size)

        # Placeholder - replace with actual queue initialization
        self.raw_frames_queue = multiprocessing.Queue(maxsize=config.queue_max_size)
        self.detections_queue = multiprocessing.Queue(maxsize=config.queue_max_size)
        self.viewport_queue = multiprocessing.Queue(maxsize=config.queue_max_size)