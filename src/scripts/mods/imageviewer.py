import time
from PIL import Image, ImageSequence, ImageOps
from mods.samplebase import SampleBase

W, H = 192, 64


def fit_frame(img, fit):
    img = img.convert('RGBA')
    bg = Image.new('RGBA', img.size, (0, 0, 0, 255))
    img = Image.alpha_composite(bg, img).convert('RGB')
    if fit == 'stretch':
        return img.resize((W, H), Image.LANCZOS)
    if fit == 'contain':
        scale = min(W / float(img.width), H / float(img.height))
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
        out = Image.new('RGB', (W, H))
        out.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
        return out
    return ImageOps.fit(img, (W, H), Image.LANCZOS)  # cover


def load_frames(path, fit='cover', max_frames=400):
    img = Image.open(path)
    frames = []
    for frame in ImageSequence.Iterator(img):
        duration = frame.info.get('duration', img.info.get('duration', 100)) or 100
        frames.append((fit_frame(frame.copy(), fit), max(20, duration) / 1000.0))
        if len(frames) >= max_frames:
            break
    return frames


class ImageViewer(SampleBase):
    """Shows a still image or plays an animated GIF/WebP/APNG."""

    def __init__(self, matrix, path=None, fit='cover', **options):
        super(ImageViewer, self).__init__(matrix)
        self.path = path
        self.fit = fit
        self.frames = []

    def run(self):
        try:
            self.frames = load_frames(self.path, self.fit)
        except Exception as e:
            print(f"Could not open image {self.path}: {e}")
            return
        if len(self.frames) == 1:
            while self.running:
                self.matrix.SetImage(self.frames[0][0])
                self.wait(0.5)
            return
        while self.running:
            for frame, duration in self.frames:
                if not self.running:
                    break
                self.matrix.SetImage(frame)
                time.sleep(duration)
