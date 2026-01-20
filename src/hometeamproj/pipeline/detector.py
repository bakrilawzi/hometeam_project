import cv2
import numpy as np
from multiprocessing import Process
from typing import Optional 

from hometeamproj.pipeline.queue_manager import FrameData, DetectionData
from hometeamproj.config import PipelineConfig
from queue import Empty, Full

class DetectionProcess(Process):
    """Process that detects motion in frames."""

    def __init__(
        self,
        input_queue,  # multiprocessing.Queue
        output_queue,  # multiprocessing.Queue
        config: PipelineConfig,
    ):
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self.prev_frame = None

    def run(self):
        """
        Detect motion in frames from input queue.

        TODO: Implement motion detection:
        1. Get frames from input_queue (handle timeout)
        2. Convert to grayscale
        3. Apply Gaussian blur
        4. Calculate frame difference with previous frame
        5. Apply threshold
        6. Find contours and extract bounding boxes
        7. Filter by minimum area
        8. Create DetectionData and put in output_queue
        9. Handle end of stream (None/sentinel values)
        """
        print("DetectionProcess: Starting motion detection")
        
        # TODO: Implement detection logic
        # while True:
        #     frame_data = self.input_queue.get(timeout=self.config.queue_timeout)
        #     if frame_data is None:  # End of stream
        #         break
        #     # Detect motion and queue results
        #     ...
        while True:
            try:
                frame_data  = self.input_queue.get(timeout=self.config.queue_timeout) #handle size as well TODO
            except Empty:
                continue
            if frame_data is None or frame_data.frame.size == 0 :
                self.output_queue.put(None) # ensuring that the second process won't wait forever 
                break
            try:
               gray = cv2.cvtColor(frame_data.frame,cv2.COLOR_BGR2GRAY)
               blur = cv2.GaussianBlur(gray,(21,21),0)
            except cv2.error as e :
                print(f"Opencv Error: {e}")
                break
            if self.prev_frame is None:
                self.prev_frame = blur
                continue
            frame_delta   = cv2.absdiff(self.prev_frame,blur)
            self.prev_frame = blur
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(
                             thresh.copy(),
                             cv2.RETR_EXTERNAL,
                             cv2.CHAIN_APPROX_SIMPLE
                            )

            boxes = []
            for c in contours:
                area = cv2.contourArea(c)
                if area < self.config.min_motion_area:   
                    continue
            
                x, y, w, h = cv2.boundingRect(c)
                boxes.append((x, y, w, h))
            detection = DetectionData(
            frame_id=frame_data.frame_id,
            timestamp=frame_data.timestamp,
            boxes=boxes,
        )

        try:
            self.output_queue.put(detection, timeout=self.config.queue_timeout)
        except Full:
            pass
            print("DetectionProcess: Finished detection")
