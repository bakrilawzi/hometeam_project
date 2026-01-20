"""
Main entrypoint for the HomeTeam viewport tracking pipeline.
"""

import multiprocessing as mp
from pathlib import Path

from .config import PipelineConfig
from .pipeline.queue_manager import QueueManager
from .pipeline.frame_reader import FrameReaderProcess
from .pipeline.detector import DetectionProcess
from .pipeline.viewport_worker import ViewportCalculatorProcess
from .pipeline.output_writer import OutputWriterProcess


def main():

    mp.set_start_method("spawn", force=True)


    config_path = Path(__file__).parent / "config.ini"
    config = PipelineConfig.from_file(str(config_path))


    queues = QueueManager(config)


    video_path = Path(__file__).parent / "pipeline" / "sample_video_clip.mp4"
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")


    output_dir = Path(__file__).resolve().parents[2] / "output"
    output_dir.mkdir(parents=True, exist_ok=True)


    frame_reader = FrameReaderProcess(
        input_video=str(video_path),
        output_queue=queues.raw_frames_queue,
        config=config,
    )

    detector = DetectionProcess(
        input_queue=queues.raw_frames_queue,
        output_queue=queues.detections_queue,
        config=config,
    )

    viewport_calculator = ViewportCalculatorProcess(
        input_queue=queues.detections_queue,
        output_queue=queues.viewport_queue,
        config=config,
    )

    output_writer = OutputWriterProcess(
        input_queue=queues.viewport_queue,
        output_dir=str(output_dir),
        config=config,
    )

    processes = [
        frame_reader,
        detector,
        viewport_calculator,
        output_writer,
    ]


    print("Starting HomeTeam viewport tracking pipeline...")
    for p in processes:
        p.start()


    for p in processes:
        p.join()

    print("Pipeline finished successfully.")


if __name__ == "__main__":
    main()
