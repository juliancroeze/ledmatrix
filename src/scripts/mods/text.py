import colorsys
from PIL import Image, ImageDraw
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size, text_bbox

FONTS = {
    'small': '7x13',
    'medium': '10x20',
    'large': 'texgyre-27',
}


def hex_to_rgb(value, default=(255, 255, 255)):
    try:
        value = value.lstrip('#')
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return default


class TextScroller(FrameMode):
    """Scrolling (or static) text message.

    options: text, color (#rrggbb), speed (px/s, 0 = static), size
             (small/medium/large), rainbow (bool)
    """

    FPS = 60

    def setup(self):
        o = self.options
        self.text = (o.get('text') or 'Hello!').replace('\n', '   ')[:500]
        self.color = hex_to_rgb(o.get('color', '#ffffff'))
        self.speed = max(0.0, min(float(o.get('speed', 40) or 0), 200.0))
        self.rainbow = bool(o.get('rainbow'))
        self.font = get_font(FONTS.get(o.get('size'), '10x20'))
        w, h = text_size(self.draw, self.text, self.font)
        bbox = text_bbox(self.draw, self.text, self.font)
        self.text_w = w
        # Pre-render the text once as a white mask, then colour it per frame
        self.mask = Image.new('L', (w + 2, bbox[3] + 2))
        ImageDraw.Draw(self.mask).text((-bbox[0], 0), self.text, font=self.font, fill=255)
        self.y = (self.HEIGHT - (bbox[1] + bbox[3])) // 2
        self.static = self.speed == 0 and w <= self.WIDTH
        self.x = (self.WIDTH - w) // 2 if self.static else float(self.WIDTH)
        self.hue = 0.0
        if self.speed == 0 and not self.static:
            self.speed = 40.0

    def render(self, dt):
        self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill=(0, 0, 0))
        if self.rainbow:
            self.hue = (self.hue + dt * 0.15) % 1.0
            color = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(self.hue, 1, 1))
        else:
            color = self.color
        if not self.static:
            self.x -= self.speed * dt
            if self.x < -self.text_w:
                self.x = float(self.WIDTH)
        self.image.paste(color, (int(self.x), self.y), self.mask)
