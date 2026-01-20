import os
import cv2
import traceback
from multiprocessing import Process
from queue import Empty

from hometeamproj.pipeline.queue_manager import ViewportData
from hometeamproj.config import PipelineConfig


class OutputWriterProcess(Process):
    def __init__(self, input_queue, output_dir: str, config: PipelineConfig):
        super().__init__()
        self.input_queue = input_queue
        self.output_dir = output_dir
        self.config = config

    def _viewport_rect(self, center, size):
        cx, cy = center
        vw, vh = size
        x1 = int(cx - vw // 2)
        y1 = int(cy - vh // 2)
        x2 = int(cx + vw // 2)
        y2 = int(cy + vh // 2)
        return x1, y1, x2, y2

    def _clamp_rect(self, x1, y1, x2, y2, frame_shape):
        h, w = frame_shape[:2]
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w))
        y2 = max(0, min(y2, h))
        if x2 <= x1:
            x2 = min(w, x1 + 1)
        if y2 <= y1:
            y2 = min(h, y1 + 1)
        return x1, y1, x2, y2

    def run(self):
        print("OutputWriterProcess: Starting output writing")
        print("OutputWriterProcess: writing to", os.path.abspath(self.output_dir))

        frames_dir = os.path.join(self.output_dir, "frames")
        viewport_dir = os.path.join(self.output_dir, "viewport")
        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(viewport_dir, exist_ok=True)

        video_writer = None
        viewport_writer = None

        out_fps = float(getattr(self.config, "target_fps", 30.0))
        out_fps = max(1.0, out_fps)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        full_video_path = os.path.join(self.output_dir, "output_full.mp4")
        viewport_video_path = os.path.join(self.output_dir, "output_viewport.mp4")

        try:
            while True:
                try:
                    viewport_data: ViewportData = self.input_queue.get(timeout=self.config.queue_timeout)
                    print(viewport_data)
                except Empty:
                    continue

                if viewport_data is None:
                    print("OutputWriterProcess: got sentinel None, stopping.")
                    break

                print("OutputWriterProcess: got frame", viewport_data.frame_id)

                frame = viewport_data.frame
                if frame is None or not hasattr(frame, "shape"):
                    print("OutputWriterProcess: bad frame, skipping.")
                    continue

                frame_h, frame_w = frame.shape[:2]

                if video_writer is None:
                    video_writer = cv2.VideoWriter(full_video_path, fourcc, out_fps, (frame_w, frame_h))
                    print("OutputWriterProcess: full writer opened =", video_writer.isOpened())

                vp_w, vp_h = map(int, viewport_data.viewport_size)

                if viewport_writer is None:
                    viewport_writer = cv2.VideoWriter(viewport_video_path, fourcc, out_fps, (vp_w, vp_h))
                    print("OutputWriterProcess: viewport writer opened =", viewport_writer.isOpened())

                vis = frame.copy()

                x1, y1, x2, y2 = self._viewport_rect(viewport_data.viewport_center, (vp_w, vp_h))
                x1, y1, x2, y2 = self._clamp_rect(x1, y1, x2, y2, frame.shape)

                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

                crop = frame[y1:y2, x1:x2].copy()
                if crop.shape[1] != vp_w or crop.shape[0] != vp_h:
                    crop = cv2.resize(crop, (vp_w, vp_h), interpolation=cv2.INTER_AREA)

                frame_path = os.path.join(frames_dir, f"frame_{viewport_data.frame_id:06d}.jpg")
                crop_path = os.path.join(viewport_dir, f"viewport_{viewport_data.frame_id:06d}.jpg")

                ok1 = cv2.imwrite(frame_path, vis)
                ok2 = cv2.imwrite(crop_path, crop)
                if not ok1 or not ok2:
                    print("OutputWriterProcess: imwrite failed:", frame_path, crop_path)

                if video_writer is not None:
                    video_writer.write(vis)
                if viewport_writer is not None:
                    viewport_writer.write(crop)

        except Exception:
            traceback.print_exc()
        finally:
            if video_writer is not None:
                video_writer.release()
            if viewport_writer is not None:
                viewport_writer.release()

        print("OutputWriterProcess: Finished writing output")
