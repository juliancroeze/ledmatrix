import random
import time
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size

W, H = 192, 64
PADDLE_H = 14
PADDLE_SPEED = 70.0


class Pong(FrameMode):
    """Pong: left paddle is player 1, right paddle is the computer unless
    a second player sends input (then it becomes player 2)."""

    FPS = 60

    def setup(self):
        self.p1 = H / 2 - PADDLE_H / 2
        self.p2 = H / 2 - PADDLE_H / 2
        self.held = {1: 0, 2: 0}
        self.p2_human_until = 0
        self.score = [0, 0]
        self.serve(direction=random.choice((-1, 1)))

    def serve(self, direction):
        self.bx, self.by = W / 2, H / 2
        self.speed = 70.0
        self.vx = direction * self.speed
        self.vy = random.uniform(-30, 30)
        self.pause = 0.8

    def set_paddle(self, player, pos):
        """Absolute paddle position from a touch slider, pos in 0..1."""
        y = max(0.0, min(1.0, float(pos))) * (H - PADDLE_H)
        if player == 2:
            self.p2 = y
            self.p2_human_until = time.time() + 10
        else:
            self.p1 = y

    def handle_input(self, action, pressed=True, player=1):
        player = 2 if player == 2 else 1
        if player == 2:
            self.p2_human_until = time.time() + 10
        if action == 'UP':
            self.held[player] = -1 if pressed else (0 if self.held[player] == -1 else self.held[player])
        elif action == 'DOWN':
            self.held[player] = 1 if pressed else (0 if self.held[player] == 1 else self.held[player])
        elif action in ('A', 'B') and pressed and max(self.score) >= 10:
            self.score = [0, 0]

    def get_state(self):
        return {'score': self.score[0], 'cpu': self.score[1], 'two_player': time.time() < self.p2_human_until}

    def render(self, dt):
        # paddles
        self.p1 += self.held[1] * PADDLE_SPEED * dt
        if time.time() < self.p2_human_until:
            self.p2 += self.held[2] * PADDLE_SPEED * dt
        else:
            target = self.by - PADDLE_H / 2 if self.vx > 0 else H / 2 - PADDLE_H / 2
            diff = target - self.p2
            self.p2 += max(-52 * dt, min(52 * dt, diff))
        self.p1 = max(0, min(H - PADDLE_H, self.p1))
        self.p2 = max(0, min(H - PADDLE_H, self.p2))

        if max(self.score) < 10:
            if self.pause > 0:
                self.pause -= dt
            else:
                self.step_ball(dt)

        d = self.draw
        d.rectangle((0, 0, W, H), fill=(0, 0, 0))
        for y in range(0, H, 4):
            d.rectangle((W // 2, y, W // 2, y + 1), fill=(40, 40, 60))
        font = get_font('10x20')
        s1, s2 = str(self.score[0]), str(self.score[1])
        w1, _ = text_size(d, s1, font)
        d.text((W // 2 - 12 - w1, 3), s1, font=font, fill=(70, 70, 110))
        d.text((W // 2 + 12, 3), s2, font=font, fill=(70, 70, 110))
        d.rectangle((3, int(self.p1), 5, int(self.p1) + PADDLE_H - 1), fill=(0, 220, 255))
        d.rectangle((W - 6, int(self.p2), W - 4, int(self.p2) + PADDLE_H - 1), fill=(255, 60, 160))
        if max(self.score) < 10:
            d.rectangle((int(self.bx) - 1, int(self.by) - 1, int(self.bx) + 1, int(self.by) + 1), fill=(255, 255, 255))
        else:
            small = get_font('6x10')
            msg = 'YOU WIN!' if self.score[0] > self.score[1] else ('P2 WINS' if time.time() < self.p2_human_until else 'CPU WINS')
            w, _ = text_size(d, msg, font)
            d.text((W // 2 - w // 2, 26), msg, font=font, fill=(255, 220, 0))
            w, _ = text_size(d, 'A = play again', small)
            d.text((W // 2 - w // 2, 48), 'A = play again', font=small, fill=(160, 160, 180))

    def step_ball(self, dt):
        self.bx += self.vx * dt
        self.by += self.vy * dt
        if self.by < 1:
            self.by, self.vy = 1, abs(self.vy)
        elif self.by > H - 2:
            self.by, self.vy = H - 2, -abs(self.vy)
        # left paddle
        if self.vx < 0 and self.bx <= 7 and self.bx >= 2:
            if self.p1 - 1 <= self.by <= self.p1 + PADDLE_H + 1:
                self.bounce(self.p1, 1)
        if self.vx > 0 and self.bx >= W - 8 and self.bx <= W - 3:
            if self.p2 - 1 <= self.by <= self.p2 + PADDLE_H + 1:
                self.bounce(self.p2, -1)
        if self.bx < -2:
            self.score[1] += 1
            self.serve(1)
        elif self.bx > W + 2:
            self.score[0] += 1
            self.serve(-1)

    def bounce(self, paddle_y, direction):
        offset = (self.by - (paddle_y + PADDLE_H / 2)) / (PADDLE_H / 2)
        self.speed = min(self.speed * 1.07, 190)
        self.vx = direction * self.speed
        self.vy = offset * self.speed * 0.7
