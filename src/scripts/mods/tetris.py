import random
import time
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size

COLS, ROWS, CELL = 10, 20, 3
WELL_X = (192 - COLS * CELL) // 2
WELL_Y = 2

SHAPES = {
    'I': [(0, 1), (1, 1), (2, 1), (3, 1)],
    'O': [(1, 0), (2, 0), (1, 1), (2, 1)],
    'T': [(1, 0), (0, 1), (1, 1), (2, 1)],
    'S': [(1, 0), (2, 0), (0, 1), (1, 1)],
    'Z': [(0, 0), (1, 0), (1, 1), (2, 1)],
    'J': [(0, 0), (0, 1), (1, 1), (2, 1)],
    'L': [(2, 0), (0, 1), (1, 1), (2, 1)],
}
COLORS = {
    'I': (0, 220, 255), 'O': (255, 210, 0), 'T': (190, 60, 255),
    'S': (60, 255, 90), 'Z': (255, 50, 70), 'J': (40, 90, 255), 'L': (255, 140, 0),
}
LINE_POINTS = [0, 100, 300, 500, 800]


def rotate(cells, kind):
    if kind == 'O':
        return cells
    size = 4 if kind == 'I' else 3
    return [(size - 1 - y, x) for x, y in cells]


class Tetris(FrameMode):
    FPS = 30

    def setup(self):
        self.reset_game()

    def reset_game(self):
        with self.lock:
            self.grid = [[None] * COLS for _ in range(ROWS)]
            self.bag = []
            self.next_kind = self.take()
            self.score = 0
            self.lines = 0
            self.level = 1
            self.game_over = False
            self.fall_timer = 0.0
            self.flash_rows = []
            self.flash_timer = 0.0
            self.spawn()

    def take(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self):
        self.kind = self.next_kind
        self.next_kind = self.take()
        self.cells = list(SHAPES[self.kind])
        self.px, self.py = 3, 0
        if not self.fits(self.cells, self.px, self.py):
            self.game_over = True

    def fits(self, cells, px, py):
        for x, y in cells:
            gx, gy = px + x, py + y
            if gx < 0 or gx >= COLS or gy >= ROWS:
                return False
            if gy >= 0 and self.grid[gy][gx] is not None:
                return False
        return True

    def try_move(self, dx, dy):
        if self.fits(self.cells, self.px + dx, self.py + dy):
            self.px += dx
            self.py += dy
            return True
        return False

    def try_rotate(self):
        new = rotate(self.cells, self.kind)
        for kick in (0, -1, 1, -2, 2):
            if self.fits(new, self.px + kick, self.py):
                self.cells = new
                self.px += kick
                return

    def lock_piece(self):
        for x, y in self.cells:
            gy = self.py + y
            if gy >= 0:
                self.grid[gy][self.px + x] = COLORS[self.kind]
        full = [y for y in range(ROWS) if all(self.grid[y])]
        if full:
            self.flash_rows = full
            self.flash_timer = 0.25
        else:
            self.spawn()

    def clear_rows(self):
        n = len(self.flash_rows)
        for y in self.flash_rows:
            del self.grid[y]
            self.grid.insert(0, [None] * COLS)
        self.flash_rows = []
        self.lines += n
        self.score += LINE_POINTS[n] * self.level
        self.level = 1 + self.lines // 10
        self.spawn()

    def handle_input(self, action, pressed=True):
        if not pressed:
            return
        with self.lock:
            if self.game_over:
                if action in ('A', 'B'):
                    self.reset_game()
                return
            if self.flash_rows:
                return
            if action == 'LEFT':
                self.try_move(-1, 0)
            elif action == 'RIGHT':
                self.try_move(1, 0)
            elif action == 'DOWN':
                if self.try_move(0, 1):
                    self.score += 1
                    self.fall_timer = 0
            elif action in ('UP', 'A'):
                self.try_rotate()
            elif action == 'B':
                while self.try_move(0, 1):
                    self.score += 2
                self.lock_piece()

    def get_state(self):
        return {'score': self.score, 'lines': self.lines, 'level': self.level, 'game_over': self.game_over}

    # -- drawing -----------------------------------------------------------
    def cell(self, gx, gy, color, ox=WELL_X, oy=WELL_Y):
        x, y = ox + gx * CELL, oy + gy * CELL
        self.draw.rectangle((x, y, x + CELL - 1, y + CELL - 1), fill=color)

    def render(self, dt):
        if not self.game_over:
            if self.flash_rows:
                self.flash_timer -= dt
                if self.flash_timer <= 0:
                    self.clear_rows()
            else:
                self.fall_timer += dt
                interval = max(0.08, 0.8 - (self.level - 1) * 0.07)
                if self.fall_timer >= interval:
                    self.fall_timer = 0
                    if not self.try_move(0, 1):
                        self.lock_piece()

        d = self.draw
        d.rectangle((0, 0, 191, 63), fill=(0, 0, 0))
        # well frame
        d.rectangle((WELL_X - 2, WELL_Y - 2, WELL_X + COLS * CELL + 1, WELL_Y + ROWS * CELL + 1), outline=(60, 60, 90))
        for y in range(ROWS):
            flashing = y in self.flash_rows
            for x in range(COLS):
                c = self.grid[y][x]
                if flashing:
                    self.cell(x, y, (255, 255, 255))
                elif c:
                    self.cell(x, y, c)
        if not self.game_over and not self.flash_rows:
            # ghost piece
            gy = self.py
            while self.fits(self.cells, self.px, gy + 1):
                gy += 1
            r, g, b = COLORS[self.kind]
            for x, y in self.cells:
                if gy + y >= 0:
                    self.cell(self.px + x, gy + y, (r // 6, g // 6, b // 6))
            for x, y in self.cells:
                if self.py + y >= 0:
                    self.cell(self.px + x, self.py + y, COLORS[self.kind])

        small = get_font('5x7')
        big = get_font('7x13')
        label = (110, 110, 150)
        d.text((10, 6), 'SCORE', font=small, fill=label)
        d.text((10, 15), str(self.score), font=big, fill=(255, 255, 255))
        d.text((10, 34), 'LINES', font=small, fill=label)
        d.text((10, 43), str(self.lines), font=big, fill=(255, 255, 255))
        d.text((44, 34), 'LVL', font=small, fill=label)
        d.text((44, 43), str(self.level), font=big, fill=(255, 255, 255))
        nx = WELL_X + COLS * CELL + 16
        d.text((nx, 6), 'NEXT', font=small, fill=label)
        for x, y in SHAPES[self.next_kind]:
            px, py = nx + x * 4, 18 + y * 4
            d.rectangle((px, py, px + 3, py + 3), fill=COLORS[self.next_kind])

        if self.game_over:
            d.rectangle((WELL_X - 8, 22, WELL_X + COLS * CELL + 7, 42), fill=(0, 0, 0), outline=(255, 50, 70))
            w, _ = text_size(d, 'GAME OVER', small)
            d.text((96 - w // 2, 25), 'GAME OVER', font=small, fill=(255, 50, 70))
            w, _ = text_size(d, 'A = again', small)
            d.text((96 - w // 2, 33), 'A = again', font=small, fill=(200, 200, 200))
