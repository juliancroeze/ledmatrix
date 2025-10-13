from mods.samplebase import SampleBase
import threading
from PIL import Image, ImageDraw
import time
import random
class FlappyBird(SampleBase):
    def __init__(self, matrix):
        print("FlappyBird instance created")
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
        self.velocity = 0
        self.jump_strength = 15

        self.birdX = 10
        self.birdY = 2

        self.pipe_width = 20
        self.pipe_gap = 25
        self.pipe_speed = 60
        self.pipes = [self.create_pipe()]

        self.image = Image.new('RGB', (self.WIDTH, self.HEIGHT), color='black')
        self.draw = ImageDraw.Draw(self.image)
        
        self.direction_lock = threading.Lock()

        self.bird = Bird(self.draw, self.GRID_SIZE, self.jump_strength)

        self.last_update_time = time.time()

    def run(self):

        while self.running:
            if not self.game_over:
                current_time = time.time()
                dt = current_time - self.last_update_time

                self.bird.update(self.gravity, dt)

                for pipe in self.pipes:
                    pipe.update(self.pipe_speed, dt)
                    if pipe.x + pipe.width <= 0:
                        self.pipes.remove(pipe)



                if self.pipes[-1].x < self.WIDTH - (self.WIDTH/2):
                    self.pipes.append(self.create_pipe())

                self.last_update_time = current_time

            self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill="black")

            for pipe in self.pipes:
                pipe.draw(self.draw, self.HEIGHT)

            self.bird.draw_bird()



            self.matrix.SetImage(self.image)

    def create_pipe(self):
        gap_y = random.randint(10, self.HEIGHT - self.pipe_gap - 10)
        return Pipe(self.WIDTH, self.pipe_width, gap_y, self.pipe_gap)

class Bird():
    def __init__(self, draw, GRID_SIZE, jump_strength):
        self.x = 10
        self.y = 2
        self.draw = draw
        self.GRID_SIZE = GRID_SIZE
        self.jump_strength = jump_strength
        self.velocity = 0

    def update(self, gravity, dt):
        self.velocity += gravity * dt
        self.y += self.velocity *dt

        #Game Over states
        if self.y < 0:
            self.y = 0
        elif self.y + self.GRID_SIZE > 64:
            self.y = 64 - self.GRID_SIZE

    def draw_bird(self):
        y = int(self.y)
        self.draw.rectangle((self.x, y, self.x + self.GRID_SIZE, y + self.GRID_SIZE), fill="yellow")

    def flap(self):
        print("Jump")
        self.velocity = -self.jump_strength

class Pipe():
    def __init__(self, x, width, gap, gap_size, color="green"):
        self.x = x
        self.width = width
        self.gap = gap
        self.gap_size = gap_size
        self.color = color

    def update(self, speed, dt):
        self.x -= speed * dt
    
    def draw(self, draw, screen_height):
        #Top Pipe
        draw.rectangle((self.x, 0, self.x + self.width, self.gap), fill=self.color)
        # Bottom pipe
        draw.rectangle(
            (self.x, self.gap + self.gap_size, self.x + self.width, screen_height),
            fill=self.color
        )




        