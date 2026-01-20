import cv2
from multiprocessing import Process
from queue import Empty, Full

from hometeamproj.pipeline.queue_manager import DetectionData
from hometeamproj.config import PipelineConfig


class DetectionProcess(Process):
    """Process that detects motion in frames."""

    def __init__(self, input_queue, output_queue, config: PipelineConfig):
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self.prev_frame = None

    def run(self):
        print("DetectionProcess: Starting motion detection")

        while True:
            # 1) Get frame
            try:
                frame_data = self.input_queue.get(timeout=self.config.queue_timeout)
            except Empty:
                continue

            # 9) End of stream: forward sentinel and exit
            if frame_data is None:
                try:
                    self.output_queue.put(None, timeout=self.config.queue_timeout)
                except Exception:
                    print("couldn't write ")
                    pass
                break


            if frame_data.frame is None:
                continue

            try:
                gray = cv2.cvtColor(frame_data.frame, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (21, 21), 0)
            except cv2.error as e:
                print(f"DetectionProcess: OpenCV error: {e}")
                continue


            if self.prev_frame is None:
                self.prev_frame = blur
                continue

            frame_delta = cv2.absdiff(self.prev_frame, blur)
            self.prev_frame = blur


            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)


            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            boxes = []
            for c in contours:

                if cv2.contourArea(c) < self.config.min_motion_area:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                boxes.append((x, y, w, h))


            detection = DetectionData(
                frame_id=frame_data.frame_id,
                frame=frame_data.frame,
                motion_boxes=boxes,
            )

            try:
                self.output_queue.put(detection, timeout=self.config.queue_timeout)
            except Full:
                print("droppping detection")
                pass

        print("DetectionProcess: Finished motion detection")
