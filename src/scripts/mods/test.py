#!/usr/bin/env python
import colorsys
from mods.samplebase import FrameMode


class PulsingColors(FrameMode):
    """Rainbow wave sweeping across the panel (the old 'test' mode)."""

    FPS = 30

    def setup(self):
        self.t = 0.0
        from PIL import Image
        # one column of colours per hue step, rebuilt each frame is cheap at 192 wide
        self.strip = Image.new('RGB', (192, 1))

    def render(self, dt):
        self.t += dt * 0.15
        px = self.strip.load()
        for x in range(192):
            r, g, b = colorsys.hsv_to_rgb((self.t + x / 384.0) % 1.0, 1, 1)
            px[x, 0] = (int(r * 255), int(g * 255), int(b * 255))
        self.image.paste(self.strip.resize((192, 64)))
