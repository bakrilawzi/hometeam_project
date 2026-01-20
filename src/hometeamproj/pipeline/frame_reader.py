# src/hometeamproj/pipeline/frame_reader.py

import time
import cv2
from multiprocessing import Process
import importlib.util
from hometeamproj.pipeline.queue_manager import FrameData , QueueManager
from pathlib import Path
from hometeamproj.config import PipelineConfig

class FrameReaderProcess(Process):
    """Process that reads frames from video file and pushes FrameData into output_queue."""

    def __init__(self, input_video: str, output_queue, config: PipelineConfig):
        super().__init__()
        self.input_video = input_video
        self.output_queue = output_queue
        self.config = config

    def run(self):
        print(f"FrameReaderProcess: Starting to read {self.input_video}")

        cap = cv2.VideoCapture(self.input_video)
        if not cap.isOpened():
            print(f"FrameReaderProcess: ERROR could not open video: {self.input_video}")
            
            try:
                self.output_queue.put(None, timeout=self.config.queue_timeout)
            except Exception:
                pass
            return

    
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if not video_fps or video_fps <= 0:
            video_fps = 30.0  

        target_fps = max(1, int(self.config.target_fps))
  
        skip_interval = max(1, int(video_fps / target_fps))

        frame_id = 0
        start_time = time.time()

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

            
                if frame_id % skip_interval == 0:
                   frame = cv2.resize(
                    frame,
                    (self.config.frame_resize_width, self.config.frame_resize_height),
                    interpolation=cv2.INTER_AREA,
                )
                   timestamp = frame_id / video_fps

                   frame_data = FrameData(frame_id=frame_id, frame=frame, timestamp=timestamp)
                   try:
                    self.output_queue.put(frame_data, timeout=self.config.queue_timeout)
                   except Exception:
                    pass
                frame_id+=1

         
            
        except KeyboardInterrupt:
            print("FrameReaderProcess: Interrupted")

        finally:
            cap.release()
            # Signal end of stream
            try:
                self.output_queue.put(None)
            except Exception:
                pass

            elapsed = time.time() - start_time
            if elapsed > 0:
                approx_out_fps = (max(0, frame_id // skip_interval)) / elapsed
                print(f"FrameReaderProcess: Approx output FPS ~ {approx_out_fps:.2f}")

            print("FrameReaderProcess: Finished reading frames")



# if __name__ == "__main__":
#     import multiprocessing as mp
#     from pathlib import Path


#     cfg_path = Path("config.ini")
#     cfg = PipelineConfig.from_file(str(cfg_path)) if cfg_path.exists() else PipelineConfig.from_file("missing.ini")
#     mp.get_start_method("spawn")
#     q = mp.Queue(maxsize=cfg.queue_max_size)

#     video_path = "/Users/bakr/Desktop/HoemTeam Project /HOMETEAMPROJ/src/hometeamproj/pipeline/sample_video_clip.mp4"  # adjust to your real path if needed
#     p = FrameReaderProcess(input_video=video_path, output_queue=q, config=cfg)

#     p.start()


#     while True:
#         item = q.get()
#         if item is None:
#             break
#         print(item.frame_id)
#         p.run()
#     p.terminate()
#     p.join()
