import colorsys
import random
from PIL import Image, ImageDraw
from mods.samplebase import FrameMode

SIZE = 32          # disc diameter in LEDs
SS = 4             # supersampling for smooth edges


def make_disc(hue):
    """A shiny optical disc in the given hue, drawn from scratch."""
    big = SIZE * SS
    img = Image.new('RGB', (big, big))
    mask = Image.new('L', (big, big))
    d = ImageDraw.Draw(img)
    md = ImageDraw.Draw(mask)
    c = big / 2.0

    def ring(r, fill, target=d):
        target.ellipse((c - r, c - r, c + r, c + r), fill=fill)

    def col(h, s, v):
        r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
        return int(r * 255), int(g * 255), int(b * 255)

    # outline + body (concentric bands give the shiny, grooved look)
    ring(c, 255, md)
    bands = 9
    for i in range(bands):
        r = c - i * (c * 0.62 / bands)
        shade = 0.55 + 0.45 * (1 - abs((i / (bands - 1)) - 0.35) * 1.4)
        ring(r, col(hue + i * 0.012, 0.85, max(0.35, min(1.0, shade))))
    # sheen: a light wedge across the disc
    sheen = Image.new('L', (big, big))
    ImageDraw.Draw(sheen).pieslice((0, 0, big, big), 200, 235, fill=150)
    img.paste((255, 255, 255), (0, 0), sheen)
    # label area, inner ring and centre hole
    ring(c * 0.36, col(hue, 0.35, 1.0))
    ring(c * 0.24, col(hue, 0.9, 0.55))
    ring(c * 0.13, 0, md)
    ring(c * 0.13, (0, 0, 0))

    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    mask = mask.resize((SIZE, SIZE), Image.LANCZOS)
    return img, mask


class Dvd(FrameMode):
    """Bouncing disc that changes colour on every wall hit,
    in the spirit of the classic DVD-player screensaver."""

    FPS = 30

    def setup(self):
        self.w = self.h = SIZE
        self.x = float(random.randint(0, 192 - self.w - 1))
        self.y = float(random.randint(0, 64 - self.h - 1))
        self.vx, self.vy = 24.0, 18.0
        self.flash = 0.0
        self.hue = random.random()
        self.recolor()

    def recolor(self):
        # jump to a clearly different hue on every bounce
        self.hue = (self.hue + random.uniform(0.2, 0.8)) % 1.0
        self.disc, self.mask = make_disc(self.hue)

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
            self.recolor()
        if hit_x and hit_y:
            self.flash = 1.0   # the legendary corner hit
        self.flash = max(0.0, self.flash - dt)
        v = int(self.flash * 120)
        self.draw.rectangle((0, 0, 192, 64), fill=(v, v, v))
        self.image.paste(self.disc, (int(self.x), int(self.y)), self.mask)
