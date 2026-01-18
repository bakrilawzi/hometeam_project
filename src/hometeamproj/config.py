import configparser
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Pipeline configuration parameters."""

    # Queue settings
    queue_max_size: int
    queue_timeout: float

    # Detection settings
    detection_threshold: float
    min_motion_area: int
    gaussian_blur_size: int

    # Viewport settings
    viewport_width: int
    viewport_height: int
    smoothing_window_size: int
    smoothing_alpha: float  # For exponential moving average

    # Processing settings
    target_fps: int
    frame_resize_width: int
    frame_resize_height: int

    @classmethod
    def from_file(cls, config_path: str) -> "PipelineConfig":
        """
        Load configuration from INI file.

        TODO: Implement configuration loading from INI file.
        Create a config.ini file with sections like:
        [queues]
        max_size = 100
        timeout = 5.0

        [detection]
        threshold = 25.0
        min_motion_area = 100
        gaussian_blur_size = 5

        [viewport]
        width = 720
        height = 480
        smoothing_window_size = 5
        smoothing_alpha = 0.3

        [processing]
        target_fps = 5
        frame_resize_width = 1280
        frame_resize_height = 720

        Use configparser.ConfigParser() to read the file.
        Parse values and return PipelineConfig instance.
        Handle missing config file by using default values.
        """
        parser = configparser.ConfigParser()
        if Path(config_path).exists():
              parser.read(config_path)
        
        def get_int(section,keys,default) -> int:
              return parser.getint(section,keys,fallback=default)
        def get_float(section,key,default) -> float:
              return parser.getfloat(section,key,fallback=default)
        
        return cls(
            queue_max_size=get_int("queues", "max_size", 50),
            queue_timeout=get_float("queues", "timeout", 5.0),
            detection_threshold=get_float("detection", "threshold", 25.0),
            min_motion_area=get_int("detection", "min_motion_area", 800),
            gaussian_blur_size=get_int("detection", "gaussian_blur_size", 5),
            viewport_width=get_int("viewport", "width", 720),
            viewport_height=get_int("viewport", "height", 480),
            smoothing_window_size=get_int("viewport", "smoothing_window_size", 5),
            smoothing_alpha=get_float("viewport", "smoothing_alpha", 0.3),
            target_fps=get_int("processing", "target_fps", 5),
            frame_resize_width=get_int("processing", "frame_resize_width", 1280),
            frame_resize_height=get_int("processing", "frame_resize_height", 720),
        )

    def __str__(self):
        return f"PipelineConfig(queue_size={self.queue_max_size}, viewport={self.viewport_width}x{self.viewport_height})"
    

# if __name__ == "__main__":
#      print(PipelineConfig.from_file("/Users/bakr/Desktop/HoemTeam Project /HOMETEAMPROJ/src/hometeamproj/config.ini"))
