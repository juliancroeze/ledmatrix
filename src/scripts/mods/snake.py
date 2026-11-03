import time
import random
import threading
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size

OPPOSITES = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}


class Snake(FrameMode):
    FPS = 60

    def __init__(self, matrix, **options):
        super(Snake, self).__init__(matrix, **options)
        self.GRID_SIZE = 4
        self.GRID_WIDTH = self.WIDTH // self.GRID_SIZE
        self.GRID_HEIGHT = self.HEIGHT // self.GRID_SIZE
        self.direction_lock = threading.Lock()
        self.high_score = 0
        self.reset_game()

    def reset_game(self):
        with self.lock:
            self.direction = "RIGHT"
            self.queue = []
            self.snake = [(5, 5), (4, 5), (3, 5)]
            self.food = self.generate_food()
            self.game_over = False
            self.score = 0
            self.speed = 0.15
            self.last_update_time = time.time()
            self.t = 0.0

    @property
    def next_direction(self):
        return self.queue[0] if self.queue else self.direction

    def generate_food(self):
        while True:
            food = (random.randint(0, self.GRID_WIDTH - 1), random.randint(0, self.GRID_HEIGHT - 1))
            if food not in self.snake:
                return food

    def change_direction(self, new_direction):
        """Queue a turn. Up to two turns are buffered so quick taps register."""
        with self.direction_lock:
            last = self.queue[-1] if self.queue else self.direction
            if new_direction in OPPOSITES and new_direction != OPPOSITES[last] and new_direction != last:
                if len(self.queue) < 2:
                    self.queue.append(new_direction)
                return True
            return False

    def handle_input(self, action, pressed=True, **_):
        if not pressed:
            return
        if self.game_over:
            if action in ('A', 'B'):
                self.reset_game()
            return
        self.change_direction(action)

    def move_snake(self):
        head_x, head_y = self.snake[0]
        with self.direction_lock:
            if self.queue:
                self.direction = self.queue.pop(0)
        dx, dy = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}[self.direction]
        new_head = (head_x + dx, head_y + dy)
        if not (0 <= new_head[0] < self.GRID_WIDTH and 0 <= new_head[1] < self.GRID_HEIGHT) or new_head in self.snake[:-1]:
            self.game_over = True
            self.high_score = max(self.high_score, self.score)
            return
        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 1
            self.food = self.generate_food()
            self.speed = max(0.05, self.speed - 0.005)
        else:
            self.snake.pop()

    def cell(self, pos, color):
        x, y = pos
        g = self.GRID_SIZE
        self.draw.rectangle((x * g, y * g, (x + 1) * g - 1, (y + 1) * g - 1), fill=color)

    def render(self, dt):
        self.t += dt
        now = time.time()
        if not self.game_over and now - self.last_update_time >= self.speed:
            self.move_snake()
            self.last_update_time = now

        d = self.draw
        d.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill="black")
        n = len(self.snake)
        for i, segment in enumerate(self.snake):
            fade = 1 - (i / max(1, n)) * 0.6
            self.cell(segment, (0, int(200 * fade), int(60 * fade)))
        self.cell(self.snake[0], (140, 255, 120))
        pulse = int(180 + 75 * abs(((self.t * 2) % 2) - 1))
        self.cell(self.food, (pulse, 20, 40))

        small = get_font('5x7')
        s = str(self.score)
        w, _ = text_size(d, s, small)
        d.text((self.WIDTH - w - 2, 1), s, font=small, fill=(90, 90, 120))

        if self.game_over:
            big = get_font('10x20')
            d.rectangle((46, 14, 146, 50), fill=(0, 0, 0), outline=(255, 50, 70))
            w, _ = text_size(d, 'GAME OVER', big)
            d.text((96 - w // 2, 17), 'GAME OVER', font=big, fill=(255, 50, 70))
            line = f'Score {self.score}  Best {self.high_score}'
            w, _ = text_size(d, line, small)
            d.text((96 - w // 2, 40), line, font=small, fill=(200, 200, 200))

    def get_game_state(self):
        return {"score": self.score, "game_over": self.game_over, "speed": self.speed}

    def get_state(self):
        return {"score": self.score, "best": self.high_score, "game_over": self.game_over}
