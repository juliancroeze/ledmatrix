import random
from mods.samplebase import FrameMode

W, H = 192, 64


class Starfield(FrameMode):
    """Flying through a 3D starfield."""

    FPS = 40

    def setup(self):
        self.stars = [self.new_star(random.uniform(0.1, 1.0)) for _ in range(160)]

    def new_star(self, z=1.0):
        return [random.uniform(-1, 1), random.uniform(-1, 1), z]

    def render(self, dt):
        d = self.draw
        d.rectangle((0, 0, W, H), fill=(0, 0, 0))
        for s in self.stars:
            pz = s[2]
            s[2] -= dt * 0.35
            if s[2] <= 0.02:
                s[:] = self.new_star()
                continue
            x = int(W / 2 + s[0] / s[2] * W / 2)
            y = int(H / 2 + s[1] / s[2] * W / 2)
            px = int(W / 2 + s[0] / pz * W / 2)
            py = int(H / 2 + s[1] / pz * W / 2)
            if not (0 <= x < W and 0 <= y < H):
                s[:] = self.new_star()
                continue
            v = int(255 * min(1, (1 - s[2]) * 1.3))
            color = (v, v, min(255, v + 40))
            d.line((px, py, x, y), fill=color)
