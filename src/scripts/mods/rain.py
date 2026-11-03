import random
from PIL import Image, ImageDraw
from mods.samplebase import FrameMode
from mods.fonts import get_font

CW, CH = 4, 7          # glyph cell size
COLS, ROWS = 192 // CW, 64 // CH + 1
GLYPHS = '0123456789ABCDEFXZ$+*<>=:'
LEVELS = 10


class MatrixRain(FrameMode):
    """Falling green glyphs, digital rain style."""

    FPS = 24

    def setup(self):
        font = get_font('tom-thumb')
        # Pre-render every glyph at every brightness level; pasting is much
        # cheaper than drawing text for each cell every frame.
        self.tiles = {}
        for g in GLYPHS:
            mask = Image.new('L', (CW, CH))
            ImageDraw.Draw(mask).text((0, 0), g, font=font, fill=255)
            self.tiles[g] = mask
        self.colors = [(int(20 * l / LEVELS), int(255 * l / LEVELS), int(70 * l / LEVELS)) for l in range(LEVELS + 1)]
        self.grid = [[None] * ROWS for _ in range(COLS)]     # glyph per cell
        self.level = [[0] * ROWS for _ in range(COLS)]       # brightness per cell
        self.drops = [self.new_drop(random.uniform(-ROWS, ROWS)) for _ in range(COLS)]
        self.acc = [0.0] * COLS

    def new_drop(self, y=None):
        return {'y': -random.randint(0, ROWS * 2) if y is None else y, 'speed': random.uniform(7, 18)}

    def render(self, dt):
        d = self.draw
        d.rectangle((0, 0, 192, 64), fill=(0, 0, 0))
        for c in range(COLS):
            drop = self.drops[c]
            self.acc[c] += dt * drop['speed']
            while self.acc[c] >= 1:
                self.acc[c] -= 1
                # fade the column
                lv = self.level[c]
                for r in range(ROWS):
                    if lv[r] > 0:
                        lv[r] -= 1
                drop['y'] += 1
                y = int(drop['y'])
                if 0 <= y < ROWS:
                    self.grid[c][y] = random.choice(GLYPHS)
                    lv[y] = LEVELS
                if y > ROWS + 4:
                    self.drops[c] = self.new_drop()
            head = int(drop['y'])
            for r in range(ROWS):
                l = self.level[c][r]
                g = self.grid[c][r]
                if l and g:
                    color = (200, 255, 210) if r == head else self.colors[l]
                    if random.random() < 0.02:
                        self.grid[c][r] = g = random.choice(GLYPHS)
                    self.image.paste(color, (c * CW, r * CH), self.tiles[g])
