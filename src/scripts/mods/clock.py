import colorsys
import datetime
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size


class Clock(FrameMode):
    """Big clock with the date underneath and a slowly cycling colour."""

    FPS = 20
    STYLES = ('default', 'mario', 'tetris')

    def setup(self):
        self.style = self.options.get('style') if self.options.get('style') in self.STYLES else 'default'
        self.face = None
        if self.style != 'default':
            from mods.clock_styles import STYLES
            self.face = STYLES[self.style]()
            self.FPS = 40
        self.hue = 0.0
        self.big = get_font('texgyre-27')
        self.mid = get_font('10x20')
        self.small = get_font('6x10')

    def render(self, dt):
        if self.face is not None:
            self.face.render(self, dt)
            return
        self.hue = (self.hue + dt * 0.03) % 1.0
        color = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(self.hue, 0.85, 1))
        dim = tuple(c // 3 for c in color)
        now = datetime.datetime.now()
        d = self.draw
        d.rectangle((0, 0, 191, 63), fill=(0, 0, 0))

        hm = now.strftime('%H:%M')
        sec = now.strftime('%S')
        w_hm, _ = text_size(d, hm, self.big)
        w_s, _ = text_size(d, sec, self.mid)
        total = w_hm + 4 + w_s
        x = (192 - total) // 2
        d.text((x, 6), hm, font=self.big, fill=color)
        d.text((x + w_hm + 4, 17), sec, font=self.mid, fill=dim)

        date = now.strftime('%A %d %B')
        w, _ = text_size(d, date, self.small)
        d.text(((192 - w) // 2, 46), date, font=self.small, fill=(150, 150, 170))

        # seconds progress bar along the bottom edge
        frac = (now.second + now.microsecond / 1e6) / 60.0
        d.line((0, 63, 191, 63), fill=(20, 20, 30))
        d.line((0, 63, int(191 * frac), 63), fill=color)
