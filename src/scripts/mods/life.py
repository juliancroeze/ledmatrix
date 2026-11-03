import random
from collections import deque
from mods.samplebase import FrameMode

CELL = 2
GW, GH = 192 // CELL, 64 // CELL


class GameOfLife(FrameMode):
    """Conway's Game of Life on a wrapping 96x32 grid. Re-seeds itself
    when the pattern dies out or gets stuck in a loop. Press A to re-seed."""

    FPS = 12

    def setup(self):
        # Precompute the 8 neighbour indices for each cell (with wrap-around)
        self.neighbours = []
        for y in range(GH):
            for x in range(GW):
                self.neighbours.append([((y + dy) % GH) * GW + (x + dx) % GW
                                        for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy])
        self.seed()

    def seed(self):
        self.cells = [1 if random.random() < 0.28 else 0 for _ in range(GW * GH)]
        self.age = [0] * (GW * GH)
        self.history = deque(maxlen=12)
        self.generation = 0
        self.hue_shift = random.random()

    def handle_input(self, action, pressed=True, **_):
        if pressed and action in ('A', 'B'):
            with self.lock:
                self.seed()

    def step(self):
        cells = self.cells
        nb = self.neighbours
        new = [0] * len(cells)
        for i, alive in enumerate(cells):
            n = 0
            for j in nb[i]:
                n += cells[j]
            if n == 3 or (alive and n == 2):
                new[i] = 1
                self.age[i] = self.age[i] + 1 if alive else 0
        self.cells = new
        self.generation += 1
        key = hash(tuple(new))
        if key in self.history or self.generation > 1500:
            self.seed()
        else:
            self.history.append(key)

    def render(self, dt):
        self.step()
        d = self.draw
        d.rectangle((0, 0, 192, 64), fill=(0, 0, 0))
        for i, alive in enumerate(self.cells):
            if alive:
                a = min(self.age[i], 20) / 20.0
                color = (int(40 + 180 * a), int(230 - 170 * a), 255)
                x, y = (i % GW) * CELL, (i // GW) * CELL
                d.rectangle((x, y, x + CELL - 1, y + CELL - 1), fill=color)
