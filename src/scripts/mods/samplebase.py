from threading import Thread
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))


class SampleBase(Thread):
    """Base class for every matrix mode.

    A mode runs in its own thread. `process()` starts it, `kill()` stops it.
    Subclasses implement `run()` and loop while `self.running` is True.

    Optional hooks a mode can implement:
      handle_input(action, pressed)  -> gamepad input from the dashboard
                                         (action is UP/DOWN/LEFT/RIGHT/A/B)
      get_state()                     -> dict sent to the dashboard (score etc.)
    """

    WIDTH = 192
    HEIGHT = 64

    def __init__(self, matrix, *args, **kwargs):
        super(SampleBase, self).__init__()
        self.daemon = True
        self.matrix = matrix
        self.running = False

    def usleep(self, value):
        time.sleep(value / 1000000.0)

    def wait(self, seconds):
        """Sleep, but wake up early when the mode is stopped."""
        end = time.time() + seconds
        while self.running and time.time() < end:
            time.sleep(min(0.05, max(0, end - time.time())))
        return self.running

    def run(self):
        return True

    def process(self):
        self.running = True
        self.start()
        return True

    def kill(self):
        self.running = False
        if self.is_alive():
            self.join(timeout=3)


class FrameMode(SampleBase):
    """A mode that draws into a 192x64 Pillow image every frame.

    Subclasses implement `render(dt)` (draw into self.image / self.draw)
    and optionally `setup()`. The base loop handles timing and pushing the
    frame to the matrix.
    """

    FPS = 30

    def __init__(self, matrix, **options):
        super(FrameMode, self).__init__(matrix)
        from PIL import Image, ImageDraw
        import threading
        self.options = options
        self.lock = threading.RLock()
        self.image = Image.new('RGB', (self.WIDTH, self.HEIGHT))
        self.draw = ImageDraw.Draw(self.image)

    def setup(self):
        pass

    def render(self, dt):
        pass

    def run(self):
        import traceback
        try:
            self.setup()
        except Exception:
            traceback.print_exc()
        last = time.time()
        errors = 0
        while self.running:
            start = time.time()
            dt = min(start - last, 0.25)
            last = start
            try:
                with self.lock:
                    self.render(dt)
                self.matrix.SetImage(self.image)
                errors = 0
            except Exception:
                errors += 1
                if errors < 3:
                    traceback.print_exc()
                time.sleep(0.5)
            spare = (1.0 / self.FPS) - (time.time() - start)
            if spare > 0:
                time.sleep(spare)
