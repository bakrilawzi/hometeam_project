# pipeline/viewport_calculator.py
"""
Viewport calculation process with state machine and smoothing.
"""

import numpy as np
from multiprocessing import Process
from collections import deque
from enum import Enum
from queue import Empty, Full

from hometeamproj.pipeline.queue_manager import DetectionData, ViewportData
from hometeamproj.config import PipelineConfig


class ViewportState(Enum):
    """Viewport calculation states."""
    TRACKING = "tracking"  # Actively following motion
    STEADY = "steady"      # Maintaining position, minimal motion


class ViewportCalculatorProcess(Process):
    """Process that calculates viewport position with state machine and smoothing."""

    def __init__(self, input_queue, output_queue, config: PipelineConfig):
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config

        self.state = ViewportState.STEADY
        self.current_viewport_center = None
        self.smoothing_buffer = deque(maxlen=int(getattr(config, "smoothing_window_size", 5)))

        
        self._motion_on_count = 0
        self._motion_off_count = 0


        self._ema_center = None


    def _get_motion_boxes(self, detection_data):

        boxes = getattr(detection_data, "boxes", None)
        if boxes is None:
            boxes = getattr(detection_data, "motion_boxes", None)
        return boxes or []

    def _get_frame_shape(self, detection_data):
         frame = detection_data.frame
         frame_id = detection_data.frame_id
         frame_shape = frame.shape if frame is not None and hasattr(frame, "shape") else None
         return frame_shape, frame_id, frame



    def calculate_roi(self, motion_boxes, frame_shape):
        """
        Calculate region of interest from motion boxes.

        Strategy implemented:
        - If no boxes: center of frame
        - Otherwise: weighted centroid of all boxes by area
          (falls back to largest box if something is off)
        """
        if frame_shape is None:
            return self.current_viewport_center or (0, 0)

        height, width = frame_shape[:2]

        if not motion_boxes:
            return (width // 2, height // 2)

        areas = []
        centers = []
        for (x, y, w, h) in motion_boxes:
            w = max(1, int(w))
            h = max(1, int(h))
            area = w * h
            cx = int(x + w / 2)
            cy = int(y + h / 2)
            areas.append(area)
            centers.append((cx, cy))

        total_area = sum(areas)
        if total_area <= 0:

            i = int(np.argmax(np.array(areas))) if areas else 0
            return centers[i] if centers else (width // 2, height // 2)

        wx = sum(c[0] * a for c, a in zip(centers, areas)) / total_area
        wy = sum(c[1] * a for c, a in zip(centers, areas)) / total_area

        return (int(round(wx)), int(round(wy)))


    def update_state(self, motion_boxes):
        """
        State transition logic with hysteresis:
        - Require N consecutive "motion present" frames to enter TRACKING
        - Require M consecutive "no motion" frames to enter STEADY

        Uses config values if present, else defaults:
        - tracking_enter_frames: 2
        - steady_enter_frames: 10
        """
        enter_tracking = int(getattr(self.config, "tracking_enter_frames", 2))
        enter_steady = int(getattr(self.config, "steady_enter_frames", 10))

        has_motion = len(motion_boxes) > 0

        if has_motion:
            self._motion_on_count += 1
            self._motion_off_count = 0
        else:
            self._motion_off_count += 1
            self._motion_on_count = 0

        if self.state == ViewportState.STEADY:
            if self._motion_on_count >= enter_tracking:
                self.state = ViewportState.TRACKING

        elif self.state == ViewportState.TRACKING:
            if self._motion_off_count >= enter_steady:
                self.state = ViewportState.STEADY

    def smooth_viewport(self, raw_viewport_center):
        """
        Smoothing pipeline:
        1) Moving average over last N samples (deque)
        2) EMA on top with alpha (config.smoothing_alpha)
        """
        raw = np.array(raw_viewport_center, dtype=np.float32)

        self.smoothing_buffer.append(tuple(raw_viewport_center))

        if len(self.smoothing_buffer) == 1:
            self._ema_center = raw
            return tuple(map(int, raw_viewport_center))
        buf = np.array(self.smoothing_buffer, dtype=np.float32)
        ma = buf.mean(axis=0)


        alpha = float(getattr(self.config, "smoothing_alpha", 0.3))
        alpha = max(0.0, min(1.0, alpha))

        if self._ema_center is None:
            self._ema_center = ma
        else:
            self._ema_center = alpha * ma + (1.0 - alpha) * self._ema_center

        smoothed = self._ema_center
        return (int(round(smoothed[0])), int(round(smoothed[1])))
    
    def clamp_viewport(self, viewport_center, frame_shape):
        x, y = viewport_center
        height, width = frame_shape[:2]
        vp_w, vp_h = int(self.config.viewport_width), int(self.config.viewport_height)

        # Clamp so that the viewport rectangle stays fully inside the frame
        x = max(vp_w // 2, min(int(x), width - vp_w // 2))
        y = max(vp_h // 2, min(int(y), height - vp_h // 2))

        return (x, y)


    def run(self):
        """
        Calculate viewport positions from detection data.

        Implements:
        1. Get DetectionData from input_queue (handle timeout)
        2. Update state machine based on motion
        3. Calculate ROI from motion boxes
        4. Apply smoothing
        5. Clamp to boundaries
        6. Create ViewportData and put in output_queue
        7. Forward sentinel None and exit
        """
        print("ViewportCalculatorProcess: Starting viewport calculation")

        while True:
            try:
                detection_data = self.input_queue.get(timeout=self.config.queue_timeout)
                
            except Empty:
                continue
            # print(detection_data)

            if detection_data is None:
                try:
                    self.output_queue.put(None, timeout=self.config.queue_timeout)
                except Exception:
                    pass
                break

            motion_boxes = self._get_motion_boxes(detection_data)
            frame_shape , frame_id , frame = self._get_frame_shape(detection_data)


            if self.current_viewport_center is None:
                if frame_shape is not None:
                    h, w = frame_shape[:2]
                    self.current_viewport_center = (w // 2, h // 2)
                else:
                    self.current_viewport_center = (0, 0)

     
            self.update_state(motion_boxes)


            roi_center = self.calculate_roi(motion_boxes, frame_shape)


            if self.state == ViewportState.TRACKING:
                raw_center = roi_center
            else:
                raw_center = self.current_viewport_center


            smoothed_center = self.smooth_viewport(raw_center)


            if frame_shape is not None:
                clamped_center = self.clamp_viewport(smoothed_center, frame_shape)
            else:
                clamped_center = smoothed_center

            self.current_viewport_center = clamped_center


            frame_id = getattr(detection_data, "frame_id", None)
            

            vp = ViewportData(
            frame_id=frame_id,
            frame=frame,
            viewport_center=clamped_center,  # (x, y)
            viewport_size=(int(self.config.viewport_width), int(self.config.viewport_height)),
            )
            
            try:
                self.output_queue.put(vp, timeout=self.config.queue_timeout)
            except Full:
                pass
            
            if vp is None:

                try:
                    vp = ViewportData(frame_id,frame , clamped_center[0], clamped_center[1])
                except Exception as e:
                    print("ViewportCalculatorProcess: ERROR creating ViewportData:", e)
                    continue

            try:
                self.output_queue.put(vp, timeout=self.config.queue_timeout)
            except Full:
    
                pass

        print("ViewportCalculatorProcess: Finished viewport calculation")
