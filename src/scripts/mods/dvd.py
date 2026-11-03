import os
import random
from PIL import Image, ImageChops
from mods.samplebase import FrameMode

HERE = os.path.dirname(__file__)


class Dvd(FrameMode):
    """Bouncing logo that changes colour on every wall hit."""

    FPS = 30

    def setup(self):
        self.logo = Image.open(os.path.join(HERE, 'images', 'ronalddvd.bmp')).convert('RGB')
        self.w, self.h = self.logo.size
        self.x = float(random.randint(0, 192 - self.w - 1))
        self.y = float(random.randint(0, 64 - self.h - 1))
        self.vx, self.vy = 24.0, 18.0
        self.flash = 0.0
        self.tint()

    def tint(self):
        hue_colors = [(255, 80, 80), (80, 255, 120), (80, 160, 255), (255, 220, 60), (255, 90, 255), (60, 255, 255)]
        color = random.choice(hue_colors)
        self.tinted = ImageChops.multiply(self.logo, Image.new('RGB', self.logo.size, color))

    def render(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        hit_x = hit_y = False
        if self.x <= 0 or self.x >= 192 - self.w:
            self.vx *= -1
            self.x = max(0, min(192 - self.w, self.x))
            hit_x = True
        if self.y <= 0 or self.y >= 64 - self.h:
            self.vy *= -1
            self.y = max(0, min(64 - self.h, self.y))
            hit_y = True
        if hit_x or hit_y:
            self.tint()
        if hit_x and hit_y:
            self.flash = 1.0   # the legendary corner hit
        self.flash = max(0.0, self.flash - dt)
        v = int(self.flash * 120)
        self.draw.rectangle((0, 0, 192, 64), fill=(v, v, v))
        self.image.paste(self.tinted, (int(self.x), int(self.y)))
