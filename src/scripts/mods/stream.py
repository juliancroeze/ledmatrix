import base64
import threading
import time
from io import BytesIO
from PIL import Image
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size


class VideoStream(FrameMode):
    """Shows frames streamed from a browser (webcam or screen share).

    The browser already scales/crops frames to 192x64, so the server only
    decodes them. Frames arrive as raw JPEG bytes (new dashboard) or as a
    base64 data URL (old dashboard).
    """

    FPS = 60
    LABEL = 'Waiting for stream'

    def __init__(self, matrix, **options):
        super(VideoStream, self).__init__(matrix, **options)
        self.frame_lock = threading.Lock()
        self.current_frame = None
        self.last_frame_time = 0
        self.frames_received = 0
        self._shown = None
        self.t = 0

    def update_frame(self, data):
        try:
            if isinstance(data, str):
                data = base64.b64decode(data.split(',', 1)[-1])
            image = Image.open(BytesIO(data)).convert('RGB')
            if image.size != (self.WIDTH, self.HEIGHT):
                image = image.resize((self.WIDTH, self.HEIGHT), Image.BILINEAR)
            with self.frame_lock:
                self.current_frame = image
                self.last_frame_time = time.time()
                self.frames_received += 1
            return True
        except Exception as e:
            print(f"Error updating frame: {e}")
            return False

    def render(self, dt):
        self.t += dt
        with self.frame_lock:
            frame = self.current_frame
        if frame is not None and time.time() - self.last_frame_time < 5:
            if frame is not self._shown:
                self.image.paste(frame)
                self._shown = frame
            return
        # Idle screen: pulsing dots while waiting for the browser
        self._shown = None
        self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill=(0, 0, 0))
        font = get_font('6x10')
        w, h = text_size(self.draw, self.LABEL, font)
        self.draw.text(((self.WIDTH - w) // 2, 22), self.LABEL, font=font, fill=(140, 140, 160))
        for i in range(3):
            phase = (self.t * 2 - i * 0.3) % 1.0
            v = int(60 + 195 * max(0, 1 - abs(phase - 0.5) * 3))
            x = self.WIDTH // 2 - 8 + i * 8
            self.draw.rectangle((x, 38, x + 3, 41), fill=(v // 2, v // 3, v))

    def get_state(self):
        return {'frames': self.frames_received}


class Webcam(VideoStream):
    LABEL = 'Waiting for camera'


class ScreenShare(VideoStream):
    LABEL = 'Waiting for screen'
