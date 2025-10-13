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
        
        # Game constants
        self.WIDTH = 192
        self.HEIGHT = 64
        self.GRID_SIZE = 4  # Size of each snake segment/food
        self.GRID_WIDTH = self.WIDTH // self.GRID_SIZE
        self.GRID_HEIGHT = self.HEIGHT // self.GRID_SIZE
        
        # Game state
        self.direction = "RIGHT"  # Initial direction
        self.next_direction = "RIGHT"  # Next direction (for preventing 180° turns)
        self.snake = [(5, 5), (4, 5), (3, 5)]  # Snake body positions
        self.food = self.generate_food()
        self.game_over = False
        self.score = 0
        self.speed = 0.15  # Snake speed (seconds between moves)
        
        # Create a black canvas
        self.image = Image.new('RGB', (self.WIDTH, self.HEIGHT), color='black')
        self.draw = ImageDraw.Draw(self.image)
        
        # Movement control
        self.direction_lock = threading.Lock()
        self.last_update_time = time.time()

    def generate_food(self):
        """Generate food in a position not occupied by the snake"""
        while True:
            food = (random.randint(0, self.GRID_WIDTH - 1), 
                   random.randint(0, self.GRID_HEIGHT - 1))
            if food not in self.snake:
                return food

    def change_direction(self, new_direction):
        """Change snake direction ensuring it can't go backwards"""
        with self.direction_lock:
            # Prevent 180-degree turns
            opposites = {
                "UP": "DOWN",
                "DOWN": "UP",
                "LEFT": "RIGHT",
                "RIGHT": "LEFT"
            }
            
            # Only change direction if it's not the opposite of current direction
            if new_direction != opposites.get(self.direction):
                self.next_direction = new_direction
                return True
            return False

    def move_snake(self):
        """Move the snake in the current direction"""
        # Get the head position
        head_x, head_y = self.snake[0]
        
        # Update direction
        with self.direction_lock:
            self.direction = self.next_direction
        
        # Calculate new head position based on direction
        if self.direction == "UP":
            new_head = (head_x, head_y - 1)
        elif self.direction == "DOWN":
            new_head = (head_x, head_y + 1)
        elif self.direction == "LEFT":
            new_head = (head_x - 1, head_y)
        elif self.direction == "RIGHT":
            new_head = (head_x + 1, head_y)
        
        # Check if the snake hits the wall
        new_head_x, new_head_y = new_head
        if (new_head_x < 0 or new_head_x >= self.GRID_WIDTH or
            new_head_y < 0 or new_head_y >= self.GRID_HEIGHT):
            self.game_over = True
            return
        
        # Check if the snake hits itself
        if new_head in self.snake[:-1]:  # Exclude the tail which will move
            self.game_over = True
            return
        
        # Add the new head
        self.snake.insert(0, new_head)
        
        # Check if the snake eats the food
        if new_head == self.food:
            self.score += 1
            self.food = self.generate_food()
            # Snake grows, so we don't remove the tail
            # Increase speed (cap at 0.05 seconds)
            if self.speed > 0.05:
                self.speed = max(0.05, self.speed - 0.005)
        else:
            # Remove the tail if no food is eaten
            self.snake.pop()

    def draw_game(self):
        """Draw the current game state to the image"""
        # Clear the image
        self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill="black")
        
        # Draw the snake
        for segment in self.snake:
            x, y = segment
            self.draw.rectangle(
                (x * self.GRID_SIZE, y * self.GRID_SIZE, 
                 (x + 1) * self.GRID_SIZE - 1, (y + 1) * self.GRID_SIZE - 1), 
                fill="green")
        
        # Draw the head with a different color
        x, y = self.snake[0]
        self.draw.rectangle(
            (x * self.GRID_SIZE, y * self.GRID_SIZE, 
             (x + 1) * self.GRID_SIZE - 1, (y + 1) * self.GRID_SIZE - 1), 
            fill="lime")
        
        # Draw the food
        x, y = self.food
        self.draw.rectangle(
            (x * self.GRID_SIZE, y * self.GRID_SIZE, 
             (x + 1) * self.GRID_SIZE - 1, (y + 1) * self.GRID_SIZE - 1), 
            fill="red")
        
        # If game over, draw a border
        if self.game_over:
            self.draw.rectangle((0, 0, self.WIDTH-1, self.HEIGHT-1), outline="white")
            # Display "GAME OVER" text
            x_offset = 60
            y_offset = 30
            text_color = "red"
            # Simple pixel art for "GAME OVER"
            # This is a simplified representation - could be improved with better pixel art

    def run(self):
        super(Snake, self).run()
        
        while self.running:
            current_time = time.time()
            
            # Only update game state if not game over
            if not self.game_over and (current_time - self.last_update_time >= self.speed):
                self.move_snake()
                self.last_update_time = current_time
            
            # Draw the game
            self.draw_game()
            
            # Update the matrix
            with self.lock:
                self.matrix.SetImage(self.image)
            
            # Sleep a bit to prevent CPU hogging
            time.sleep(0.01)
    
    def reset_game(self):
        """Reset the game to initial state"""
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
        """Return the current game state as a dictionary"""
        return {
            "score": self.score,
            "game_over": self.game_over,
            "speed": self.speed
        }