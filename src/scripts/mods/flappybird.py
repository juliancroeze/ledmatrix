from mods.samplebase import SampleBase
import threading
from PIL import Image, ImageDraw
import time
class FlappyBird(SampleBase):
    def __init__(self, matrix):
        threading.Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()
        
        self.WIDTH = 192
        self.HEIGHT = 64
        self.GRID_SIZE = 8  
        self.GRID_WIDTH = self.WIDTH // self.GRID_SIZE
        self.GRID_HEIGHT = self.HEIGHT // self.GRID_SIZE
        
        self.game_over = False
        self.score = 0
        self.gravity = 20

        self.birdX = 10
        self.birdY = 2
        self.image = Image.new('RGB', (self.WIDTH, self.HEIGHT), color='black')
        self.draw = ImageDraw.Draw(self.image)
        
        self.direction_lock = threading.Lock()

        self.last_update_time = time.time()

    def run(self):
        self.bird = Bird(self.draw, self.GRID_SIZE)

        while self.running:
            if not self.game_over:
                current_time = time.time()
                dt = current_time - self.last_update_time
                self.bird.y += self.gravity * dt
                self.last_update_time = current_time

            self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill="black")

            self.bird.draw_bird()

            self.matrix.SetImage(self.image)

class Bird():
    def __init__(self, draw, GRID_SIZE):
        self.x = 10
        self.y = 2
        self.draw = draw
        self.GRID_SIZE = GRID_SIZE

    def draw_bird(self):
        y = int(self.y)
        self.draw.rectangle((self.x, self.y, self.x + self.GRID_SIZE, y + self.GRID_SIZE), fill="yellow")




        