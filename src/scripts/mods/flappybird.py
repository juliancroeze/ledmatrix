import math
import random
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size

W, H = 192, 64
GRAVITY = 170.0
FLAP = -62.0
PIPE_W = 10
GAP = 24
SPEED = 42.0
SPACING = 64


class Bird(object):
    def __init__(self):
        self.x = 30
        self.y = H / 2
        self.velocity = 0.0

    def flap(self):
        self.velocity = FLAP


class FlappyBird(FrameMode):
    FPS = 60

    def setup(self):
        self.best = 0
        self.reset_game()

    def reset_game(self):
        self.bird = Bird()
        self.pipes = []
        self.score = 0
        self.state = 'ready'   # ready -> playing -> over
        self.over_timer = 0
        self.t = 0.0
        self.ground_x = 0.0

    # Start / flap / restart depending on the game state.
    def flap(self):
        with self.lock:
            if self.state == 'ready':
                self.state = 'playing'
                self.bird.flap()
            elif self.state == 'playing':
                self.bird.flap()
            elif self.state == 'over' and self.over_timer <= 0:
                self.reset_game()

    def handle_input(self, action, pressed=True, **_):
        if pressed and action in ('A', 'B', 'UP'):
            self.flap()

    def get_state(self):
        return {'score': self.score, 'best': self.best, 'game_over': self.state == 'over'}

    def add_pipe(self):
        gap_y = random.randint(8, H - GAP - 8)
        self.pipes.append({'x': float(W), 'gap': gap_y, 'scored': False})

    def render(self, dt):
        self.t += dt
        b = self.bird
        if self.state == 'ready':
            b.y = H / 2 + 3 * math.sin(self.t * 4)
        elif self.state == 'playing':
            b.velocity += GRAVITY * dt
            b.y += b.velocity * dt
            if not self.pipes or self.pipes[-1]['x'] < W - SPACING:
                self.add_pipe()
            for p in self.pipes:
                p['x'] -= SPEED * dt
                if not p['scored'] and p['x'] + PIPE_W < b.x:
                    p['scored'] = True
                    self.score += 1
            self.pipes = [p for p in self.pipes if p['x'] + PIPE_W > 0]
            if self.collides():
                self.state = 'over'
                self.over_timer = 0.6
                self.best = max(self.best, self.score)
        else:
            self.over_timer -= dt
            if b.y < H - 4:
                b.velocity += GRAVITY * dt
                b.y = min(H - 4, b.y + b.velocity * dt)

        d = self.draw
        # sky gradient bands
        d.rectangle((0, 0, W, H), fill=(4, 6, 24))
        d.rectangle((0, 40, W, H), fill=(6, 10, 34))
        for p in self.pipes:
            x = int(p['x'])
            g = p['gap']
            d.rectangle((x, 0, x + PIPE_W, g), fill=(30, 170, 40))
            d.rectangle((x - 1, g - 3, x + PIPE_W + 1, g), fill=(60, 220, 70))
            d.rectangle((x, g + GAP, x + PIPE_W, H), fill=(30, 170, 40))
            d.rectangle((x - 1, g + GAP, x + PIPE_W + 1, g + GAP + 3), fill=(60, 220, 70))
        # bird: 5x4 body, eye, beak
        bx, by = int(b.x), int(b.y)
        d.rectangle((bx, by, bx + 4, by + 3), fill=(255, 210, 0))
        d.point((bx + 3, by + 1), fill=(0, 0, 0))
        d.rectangle((bx + 5, by + 2, bx + 6, by + 2), fill=(255, 100, 0))
        wing = (bx, by + (2 if int(self.t * 10) % 2 else 1))
        d.point(wing, fill=(255, 255, 200))

        font = get_font('7x13')
        s = str(self.score)
        w, _ = text_size(d, s, font)
        d.text((W // 2 - w // 2, 2), s, font=font, fill=(255, 255, 255))
        small = get_font('5x7')
        if self.state == 'ready':
            msg = 'Press A to flap'
            w, _ = text_size(d, msg, small)
            d.text((W // 2 - w // 2, 50), msg, font=small, fill=(180, 180, 220))
        elif self.state == 'over':
            big = get_font('10x20')
            w, _ = text_size(d, 'GAME OVER', big)
            d.text((W // 2 - w // 2, 20), 'GAME OVER', font=big, fill=(255, 60, 80))
            msg = f'Best {self.best}  -  A = again'
            w, _ = text_size(d, msg, small)
            d.text((W // 2 - w // 2, 44), msg, font=small, fill=(200, 200, 220))

    def collides(self):
        b = self.bird
        if b.y < 0 or b.y + 4 > H:
            return True
        for p in self.pipes:
            if p['x'] - 1 < b.x + 5 and p['x'] + PIPE_W + 1 > b.x:
                if b.y < p['gap'] or b.y + 4 > p['gap'] + GAP:
                    return True
        return False
