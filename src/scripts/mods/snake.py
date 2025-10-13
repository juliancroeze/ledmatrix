import time
import random
import threading
from PIL import Image, ImageDraw
from mods.samplebase import SampleBase

class Snake(SampleBase):
    def __init__(self, matrix):
        threading.Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()
        
        self.WIDTH = 192
        self.HEIGHT = 64
        self.GRID_SIZE = 4  
        self.GRID_WIDTH = self.WIDTH // self.GRID_SIZE
        self.GRID_HEIGHT = self.HEIGHT // self.GRID_SIZE
        
        self.direction = "RIGHT"  
        self.next_direction = "RIGHT"  
        self.snake = [(5, 5), (4, 5), (3, 5)]  
        self.food = self.generate_food()
        self.game_over = False
        self.score = 0
        self.speed = 0.15  
        
        self.image = Image.new('RGB', (self.WIDTH, self.HEIGHT), color='black')
        self.draw = ImageDraw.Draw(self.image)
        
        self.direction_lock = threading.Lock()
        self.last_update_time = time.time()

    def generate_food(self):
        while True:
            food = (random.randint(0, self.GRID_WIDTH - 1), 
                   random.randint(0, self.GRID_HEIGHT - 1))
            if food not in self.snake:
                return food

    def change_direction(self, new_direction):
        with self.direction_lock:
            opposites = {
                "UP": "DOWN",
                "DOWN": "UP",
                "LEFT": "RIGHT",
                "RIGHT": "LEFT"
            }
            
            if new_direction != opposites.get(self.direction):
                self.next_direction = new_direction
                return True
            return False

    def move_snake(self):
        head_x, head_y = self.snake[0]
        
        with self.direction_lock:
            self.direction = self.next_direction
        
        if self.direction == "UP":
            new_head = (head_x, head_y - 1)
        elif self.direction == "DOWN":
            new_head = (head_x, head_y + 1)
        elif self.direction == "LEFT":
            new_head = (head_x - 1, head_y)
        elif self.direction == "RIGHT":
            new_head = (head_x + 1, head_y)
        
        new_head_x, new_head_y = new_head
        if (new_head_x < 0 or new_head_x >= self.GRID_WIDTH or
            new_head_y < 0 or new_head_y >= self.GRID_HEIGHT):
            self.game_over = True
            return
        
        if new_head in self.snake[:-1]:  
            self.game_over = True
            return
        
        self.snake.insert(0, new_head)
        
        if new_head == self.food:
            self.score += 1
            self.food = self.generate_food()
            if self.speed > 0.05:
                self.speed = max(0.05, self.speed - 0.005)
        else:
            # Remove the tail if no food is eaten
            self.snake.pop()

    def draw_game(self):
        self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill="black")
        
        for segment in self.snake:
            x, y = segment
            self.draw.rectangle(
                (x * self.GRID_SIZE, y * self.GRID_SIZE, 
                 (x + 1) * self.GRID_SIZE - 1, (y + 1) * self.GRID_SIZE - 1), 
                fill="green")
        
        x, y = self.snake[0]
        self.draw.rectangle(
            (x * self.GRID_SIZE, y * self.GRID_SIZE, 
             (x + 1) * self.GRID_SIZE - 1, (y + 1) * self.GRID_SIZE - 1), 
            fill="lime")
        
        x, y = self.food
        self.draw.rectangle(
            (x * self.GRID_SIZE, y * self.GRID_SIZE, 
             (x + 1) * self.GRID_SIZE - 1, (y + 1) * self.GRID_SIZE - 1), 
            fill="red")
        
        if self.game_over:
            self.draw.rectangle((0, 0, self.WIDTH-1, self.HEIGHT-1), outline="white")
            x_offset = 60
            y_offset = 30
            text_color = "red"

    def run(self):
        super(Snake, self).run()
        
        while self.running:
            current_time = time.time()
            
            if not self.game_over and (current_time - self.last_update_time >= self.speed):
                self.move_snake()
                self.last_update_time = current_time
            
            self.draw_game()
            
            with self.lock:
                self.matrix.SetImage(self.image)
            
            time.sleep(0.01)
    
    def reset_game(self):
        with self.lock:
            self.direction = "RIGHT"
            self.next_direction = "RIGHT"
            self.snake = [(5, 5), (4, 5), (3, 5)]
            self.food = self.generate_food()
            self.game_over = False
            self.score = 0
            self.speed = 0.15
            self.last_update_time = time.time()
            
    def get_game_state(self):
        return {
            "score": self.score,
            "game_over": self.game_over,
            "speed": self.speed
        }