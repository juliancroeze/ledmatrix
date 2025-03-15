from mods.samplebase import SampleBase
from threading import Thread
from PIL import Image
import threading
import time
import os
import io
import base64

class Drawing(SampleBase):
    def __init__(self, matrix):
        Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()
        self.image = None
        # Use a path in the user's home directory which should have write permissions
        self.drawing_path = os.path.expanduser("~/user_drawing.png")
        self.needs_update = False

    def run(self):
        super(Drawing, self).run()
        # Load default image if it exists
        if os.path.exists(self.drawing_path):
            self.load_image(self.drawing_path)
        else:
            # Create a blank black image if no drawing exists
            img = Image.new('RGB', (192, 64), color='black')
            try:
                img.save(self.drawing_path)
                self.image = img
            except PermissionError:
                print(f"Permission error when saving to {self.drawing_path}")
                # Use an in-memory image instead
                self.image = img

        while self.running:
            if self.image:
                with self.lock:
                    self.matrix.SetImage(self.image)
                    self.needs_update = False
            time.sleep(0.1)  # Short sleep to prevent CPU hogging

    def load_image(self, path):
        try:
            with self.lock:
                self.image = Image.open(path).convert('RGB')
                self.image = self.image.resize((192, 64))
        except Exception as e:
            print(f"Error loading image: {e}")
            # Create a fallback black image
            self.image = Image.new('RGB', (192, 64), color='black')

    def update_from_data_url(self, data_url):
        try:
            # Extract the base64 encoded image data
            header, encoded = data_url.split(",", 1)
            image_data = base64.b64decode(encoded)
            
            # Create image from the data
            img = Image.open(io.BytesIO(image_data)).convert('RGB')
            img = img.resize((192, 64))
            
            # Try to save the image to disk for persistence
            try:
                img.save(self.drawing_path)
                print(f"Successfully saved drawing to {self.drawing_path}")
            except PermissionError:
                print(f"Permission error when saving to {self.drawing_path}")
                # Continue anyway since we have the image in memory
            
            # Update the current image
            with self.lock:
                self.image = img
                self.needs_update = True
            
            return True
        except Exception as e:
            print(f"Error processing drawing: {e}")
            return False