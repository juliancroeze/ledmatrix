from mods.samplebase import SampleBase
from threading import Thread
from PIL import Image
import threading
import time 

class Gif(SampleBase):
    def __init__(self, matrix):
        Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()

    def run(self):
        super(Gif, self).run()
        gif = self.get_img("mods/images/image.jpeg")

        while self.running:
            for frame in gif:
                self.matrix.SetImage(frame)
                time.sleep(0.1)

    def get_img(self, path):
        img = Image.open(path)
        
        seq = []
        
        try:
            while True:
                t = img.copy().convert('RGB')
                t = t.resize((192, 64))  # Resize each frame individually
                seq.append(t)
                img.seek(len(seq))  # Move to the next frame
        except EOFError:
            pass

        return seq


        


