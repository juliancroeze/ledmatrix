import time
import threading
import base64
from io import BytesIO
from PIL import Image
from mods.samplebase import SampleBase

class Webcam(SampleBase):
    def __init__(self, matrix):
        threading.Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()
        self.WIDTH = 192
        self.HEIGHT = 64
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
    def update_frame(self, image_data):
        """Update the current frame from web client"""
        try:
            image_bytes = base64.b64decode(image_data.split(',')[1])
            image = Image.open(BytesIO(image_bytes))
            
            image = image.resize((self.WIDTH, self.HEIGHT), Image.LANCZOS)
            image = image.convert('RGB')
            
            with self.frame_lock:
                self.current_frame = image
        except Exception as e:
            print(f"Error updating frame: {e}")
    
    def run(self):
        super(Webcam, self).run()
        
        while self.running:
            with self.frame_lock:
                if self.current_frame:
                    with self.lock:
                        self.matrix.SetImage(self.current_frame)
            
            time.sleep(0.01)  