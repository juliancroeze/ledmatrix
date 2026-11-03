"""Extra clock faces for the Clock mode: 'mario' and 'tetris'.

Each style is a small class with render(mode, dt) that draws into
mode.image / mode.draw (192x64).
"""
import datetime
import math
import random

from PIL import Image

from mods.fonts import get_font, text_size

W, H = 192, 64


def hhmm(t):
    return t.strftime('%H%M')


# ---------------------------------------------------------------------------
# Mario: the digits sit in ? blocks; every minute Mario walks under the
# digits that change and bumps them, with a coin popping out.
# ---------------------------------------------------------------------------
class MarioClock(object):
    GROUND = 56                       # y of the top of the ground
    BLOCK_Y, BLOCK_H, BLOCK_W = 10, 24, 26
    BLOCK_X = (36, 64, 102, 130)
    HOME = 14
    GRAVITY = 520.0
    WALK = 48.0

    def __init__(self):
        from mods import mario as M
        self.M = M
        sp = M.Sprites()
        self.mario = {k: (sp.get('cm' + k, M.BIG[k], scale=2), sp.get('cm' + k, M.BIG[k], scale=2, flip=True))
                      for k in ('stand', 'walk', 'jump')}
        self.goomba = [sp.get('cg%d' % i, M.GOOMBA[i], scale=2) for i in (0, 1)]
        self.goomba_flat = sp.get('cgf', M.GOOMBA_FLAT, scale=2)
        self.coin = sp.get('cc', M.COIN, scale=2)
        self.bg = M.SuperMario.make_bg_over(self)
        self.ground = self.make_ground()
        self.digit_font = get_font('10x20')
        self.small = get_font('tom-thumb')
        self.shown = None
        self.plan = []                # [(block index, new digit)]
        self.plan_minute = None
        self.x, self.y = float(self.HOME), float(self.GROUND - 16)
        self.vx = self.vy = 0.0
        self.facing = 1
        self.air = False
        self.anim = 0.0
        self.bumps = {}               # block -> time since bump
        self.coins = []               # [x, t]
        self.goomba_x = None
        self.goomba_flat_t = None
        self.next_goomba = 6.0
        self.pan = 0.0

    def make_ground(self):
        img = Image.new('RGB', (W, H - self.GROUND))
        px = img.load()
        for y in range(img.height):
            for x in range(W):
                if y == 0:
                    c = (120, 230, 70)
                elif y == 1:
                    c = (50, 170, 40) if x % 3 else (120, 230, 70)
                else:
                    wave = (y + int(1.5 * math.sin(x * 0.8))) % 5
                    c = (205, 95, 45) if wave == 0 else (245, 150, 85)
                px[x, y] = c
        return img

    # -- logic ------------------------------------------------------------------
    def block_center(self, i):
        return self.BLOCK_X[i] + self.BLOCK_W / 2.0

    def update(self, dt, now):
        target = hhmm(now)
        if self.shown is None:
            self.shown = list(target)
        # plan the bumps a few seconds before the minute turns over
        if not self.plan:
            nxt = now + datetime.timedelta(minutes=1)
            if now.second >= 55:
                upcoming = hhmm(nxt.replace(second=0, microsecond=0))
                self.plan = [(i, d) for i, d in enumerate(upcoming) if d != self.shown[i]]
                self.plan_minute = nxt.replace(second=0, microsecond=0)
            elif list(target) != self.shown:
                # clock was changed or we missed a minute: fix it right away
                self.plan = [(i, d) for i, d in enumerate(target) if d != self.shown[i]]
                self.plan_minute = now
        self.anim += dt
        on_ground = not self.air
        goal = None
        if self.plan:
            goal = self.block_center(self.plan[0][0]) - 4
        elif self.goomba_x is None or self.goomba_flat_t is not None:
            goal = self.HOME
        if on_ground:
            if goal is not None and abs(goal - self.x) > 1.0:
                self.vx = self.WALK * (1 if goal > self.x else -1)
                self.facing = 1 if self.vx > 0 else -1
            else:
                self.vx = 0.0
                if goal is not None:
                    self.x = goal
                if self.plan and now >= self.plan_minute - datetime.timedelta(seconds=0.3):
                    self.jump(math.sqrt(2 * self.GRAVITY * 9))
        # Goomba wanders in from the right now and then; Mario stomps it
        if self.goomba_x is None and not self.plan:
            self.next_goomba -= dt
            if self.next_goomba <= 0 and now.second < 45:
                self.goomba_x = float(W + 4)
                self.goomba_flat_t = None
        if self.goomba_x is not None:
            if self.goomba_flat_t is not None:
                self.goomba_flat_t += dt
                if self.goomba_flat_t > 0.6:
                    self.goomba_x = None
                    self.next_goomba = random.uniform(15, 30)
            else:
                self.goomba_x -= 14.0 * dt
                dist = self.goomba_x - (self.x + 8)
                if on_ground and not self.plan and 6 < dist < 22:
                    self.vx = 30.0
                    self.facing = 1
                    self.jump(150.0)
                if self.goomba_x < -20:
                    self.goomba_x = None
                    self.next_goomba = random.uniform(15, 30)
        # physics
        self.x += self.vx * dt
        if self.air:
            self.vy += self.GRAVITY * dt
            self.y += self.vy * dt
            head = self.y
            # bump a block
            if self.vy < 0:
                for i, bx in enumerate(self.BLOCK_X):
                    if bx - 2 < self.x + 4 < bx + self.BLOCK_W + 2 and head <= self.BLOCK_Y + self.BLOCK_H:
                        self.y = self.BLOCK_Y + self.BLOCK_H
                        self.vy = 40.0
                        self.bumps[i] = 0.0
                        if self.plan and self.plan[0][0] == i:
                            self.shown[i] = self.plan[0][1]
                            self.plan.pop(0)
                            self.coins.append([bx + self.BLOCK_W / 2.0 - 2, 0.0])
                        break
            # stomp the Goomba
            if (self.vy > 0 and self.goomba_x is not None and self.goomba_flat_t is None and
                    abs((self.x + 4) - (self.goomba_x + 4)) < 9 and self.y + 16 >= self.GROUND - 8):
                self.goomba_flat_t = 0.0
                self.vy = -120.0
            if self.y >= self.GROUND - 16:
                self.y = float(self.GROUND - 16)
                self.vy = 0.0
                self.air = False
                if not self.plan:
                    self.vx = 0.0
        for k in list(self.bumps):
            self.bumps[k] += dt
            if self.bumps[k] > 0.2:
                del self.bumps[k]
        for c in self.coins:
            c[1] += dt
        self.coins = [c for c in self.coins if c[1] < 0.6]
        self.pan += dt * 3.0

    def jump(self, v):
        self.vy = -v
        self.air = True

    # -- drawing ----------------------------------------------------------------
    def render(self, mode, dt):
        now = datetime.datetime.now()
        self.update(min(dt, 0.1), now)
        img, d = mode.image, mode.draw
        bw = self.bg.width
        bx = int(self.pan) % (bw - W)
        img.paste(self.bg.crop((bx, 48, bx + W, 48 + H)), (0, 0))
        img.paste(self.ground, (0, self.GROUND))
        # date, top left
        date = now.strftime('%a %d %b').upper()
        d.text((3, 2), date, font=self.small, fill=(0, 0, 0))
        d.text((2, 1), date, font=self.small, fill=(255, 255, 255))
        # blocks with digits
        for i, bx in enumerate(self.BLOCK_X):
            t = self.bumps.get(i)
            dy = -int(round(4 * math.sin(math.pi * t / 0.2))) if t is not None else 0
            self.draw_block(d, bx, self.BLOCK_Y + dy, self.shown[i] if self.shown else '0')
        # colon: two blinking coins
        if now.microsecond < 600000:
            for cy in (14, 26):
                img.paste(self.coin, (94, cy), self.coin)
        for x, t in self.coins:
            y = self.BLOCK_Y - 8 - int(28 * math.sin(min(1.0, t / 0.6) * math.pi * 0.9))
            img.paste(self.coin, (int(x), y), self.coin)
        # Goomba
        if self.goomba_x is not None:
            gx = int(self.goomba_x)
            if self.goomba_flat_t is not None:
                img.paste(self.goomba_flat, (gx, self.GROUND - 4), self.goomba_flat)
            else:
                g = self.goomba[int(self.anim * 5) % 2]
                img.paste(g, (gx, self.GROUND - 8), g)
        # Mario
        if self.air:
            frame = 'jump'
        elif abs(self.vx) > 1 and int(self.anim * 8) % 2:
            frame = 'walk'
        else:
            frame = 'stand'
        spr = self.mario[frame][0 if self.facing > 0 else 1]
        img.paste(spr, (int(round(self.x)), int(round(self.y))), spr)

    def draw_block(self, d, x, y, digit):
        w, h = self.BLOCK_W, self.BLOCK_H
        d.rectangle((x, y, x + w - 1, y + h - 1), fill=(245, 185, 0))
        d.rectangle((x, y, x + w - 1, y + h - 1), outline=(150, 80, 0))
        d.line((x + 1, y + 1, x + w - 2, y + 1), fill=(255, 235, 140))
        d.line((x + 1, y + 1, x + 1, y + h - 2), fill=(255, 235, 140))
        for cx, cy in ((x + 3, y + 3), (x + w - 4, y + 3), (x + 3, y + h - 4), (x + w - 4, y + h - 4)):
            d.point((cx, cy), fill=(150, 80, 0))
        tw, th = text_size(d, digit, self.digit_font)
        tx, ty = x + (w - tw) // 2, y + (h - 20) // 2 - 1
        d.text((tx + 1, ty + 1), digit, font=self.digit_font, fill=(255, 225, 120))
        d.text((tx, ty), digit, font=self.digit_font, fill=(110, 50, 0))


# ---------------------------------------------------------------------------
# Tetris: every digit is built from falling pieces. When a digit changes,
# its old blocks drop out and new pieces fall into place.
# ---------------------------------------------------------------------------
DIGITS = {
    '0': ["######", "######", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "######", "######"],
    '1': ["..##..", ".###..", "####..", "..##..", "..##..", "..##..", "..##..", "..##..", "######", "######"],
    '2': ["######", "######", "....##", "....##", "######", "######", "##....", "##....", "######", "######"],
    '3': ["######", "######", "....##", "....##", ".#####", ".#####", "....##", "....##", "######", "######"],
    '4': ["##..##", "##..##", "##..##", "##..##", "######", "######", "....##", "....##", "....##", "....##"],
    '5': ["######", "######", "##....", "##....", "######", "######", "....##", "....##", "######", "######"],
    '6': ["######", "######", "##....", "##....", "######", "######", "##..##", "##..##", "######", "######"],
    '7': ["######", "######", "....##", "....##", "...##.", "...##.", "..##..", "..##..", "..##..", "..##.."],
    '8': ["######", "######", "##..##", "##..##", "######", "######", "##..##", "##..##", "######", "######"],
    '9': ["######", "######", "##..##", "##..##", "######", "######", "....##", "....##", "######", "######"],
}
TETRIS_COLORS = [(0, 220, 255), (255, 210, 0), (190, 60, 255), (60, 255, 90),
                 (255, 50, 70), (40, 90, 255), (255, 140, 0)]


def decompose(digit, rng):
    """Split a digit into pieces of up to 4 cells that can each fall straight
    down into place, bottom pieces first."""
    cells = {(x, y) for y, row in enumerate(DIGITS[digit]) for x, ch in enumerate(row) if ch == '#'}
    free = set(cells)
    pieces = []

    def supported(c, piece):
        below = (c[0], c[1] + 1)
        return below not in cells or below not in free or below in piece

    while free:
        start = max(free, key=lambda c: (c[1], -c[0]))
        piece = [start]
        while len(piece) < 4:
            cands = []
            for px, py in piece:
                for n in ((px - 1, py), (px + 1, py), (px, py - 1)):
                    if n in free and n not in piece and n not in cands and supported(n, piece):
                        cands.append(n)
            if not cands:
                break
            piece.append(rng.choice(cands))
        free -= set(piece)
        pieces.append(piece)
    return pieces


class TetrisClock(object):
    CELL = 5
    TOP = 7
    DIGIT_X = (12, 46, 112, 146)
    FALL = 170.0          # px per second
    STAGGER = 0.11        # seconds between pieces of one digit

    def __init__(self):
        self.rng = random.Random()
        self.shown = [None] * 4
        self.pieces = [[] for _ in range(4)]     # per digit: dicts with cells, color, y offset, start
        self.dropping = []                       # old cells falling out: [x, y, vy, color]
        self.t = 0.0

    def build(self, i, digit, delay=0.0):
        pieces = []
        for n, cells in enumerate(decompose(digit, self.rng)):
            top = min(c[1] for c in cells)
            pieces.append(dict(cells=cells, color=self.rng.choice(TETRIS_COLORS),
                               offset=-(top + 4) * self.CELL - 8.0, start=self.t + delay + n * self.STAGGER))
        self.pieces[i] = pieces
        self.shown[i] = digit

    def update(self, dt, now):
        self.t += dt
        target = hhmm(now)
        for i, digit in enumerate(target):
            if digit != self.shown[i]:
                if self.shown[i] is not None:
                    # old blocks tumble out of the bottom
                    for p in self.pieces[i]:
                        for cx, cy in p['cells']:
                            x, y = self.cell_xy(i, cx, cy, p['offset'])
                            self.dropping.append([x, y, self.rng.uniform(-10, 10), -self.rng.uniform(0, 60), p['color']])
                self.build(i, digit, delay=0.35 if self.shown[i] is not None else i * 0.4)
        for pieces in self.pieces:
            for p in pieces:
                if self.t >= p['start'] and p['offset'] < 0:
                    p['offset'] = min(0.0, p['offset'] + self.FALL * dt)
        for c in self.dropping:
            c[3] += 300.0 * dt
            c[0] += c[2] * dt
            c[1] += c[3] * dt
        self.dropping = [c for c in self.dropping if c[1] < H + 2]

    def cell_xy(self, i, cx, cy, offset):
        return self.DIGIT_X[i] + cx * self.CELL, self.TOP + cy * self.CELL + offset

    def cell(self, d, x, y, color):
        x, y = int(round(x)), int(round(y))
        c = self.CELL
        dark = tuple(v // 3 for v in color)
        light = tuple(min(255, v + 90) for v in color)
        d.rectangle((x, y, x + c - 1, y + c - 1), fill=color)
        d.line((x, y + c - 1, x + c - 1, y + c - 1), fill=dark)
        d.line((x + c - 1, y, x + c - 1, y + c - 1), fill=dark)
        d.point((x, y), fill=light)

    def render(self, mode, dt):
        now = datetime.datetime.now()
        self.update(min(dt, 0.1), now)
        d = mode.draw
        d.rectangle((0, 0, W - 1, H - 1), fill=(0, 0, 0))
        # faint well behind the digits
        for i, x0 in enumerate(self.DIGIT_X):
            d.rectangle((x0 - 1, self.TOP + 10 * self.CELL, x0 + 6 * self.CELL, self.TOP + 10 * self.CELL),
                        fill=(30, 30, 50))
        for i, pieces in enumerate(self.pieces):
            for p in pieces:
                if self.t < p['start']:
                    continue
                for cx, cy in p['cells']:
                    x, y = self.cell_xy(i, cx, cy, p['offset'])
                    if y > -self.CELL:
                        self.cell(d, x, y, p['color'])
        for x, y, _, _, color in self.dropping:
            self.cell(d, x, y, color)
        # colon
        on = now.microsecond < 600000
        for cy in (20, 40):
            self.cell(d, 92, cy, (200, 200, 220) if on else (40, 40, 55))
        # seconds: a line of tiny blocks along the bottom
        n = int(now.second / 60.0 * 47)
        for k in range(48):
            x = 1 + k * 4
            col = TETRIS_COLORS[(k // 4) % len(TETRIS_COLORS)] if k <= n else (25, 25, 40)
            d.rectangle((x, 61, x + 2, 62), fill=col)


STYLES = {'mario': MarioClock, 'tetris': TetrisClock}
