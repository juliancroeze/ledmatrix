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
        gif = self.get_img("mods/images/ronald.png")

        while self.running:
            for frame in gif:
                self.matrix.SetImage(frame)
                time.sleep(0.1)

    def get_img(self, path):
        img = Image.open(path)
        img.resize((192, 64))

        seq = []

        try:
            while True:
                t = img.copy()
                seq.append(t.convert('RGB'))
                img.seek(len(seq))
        except EOFError:
            pass

        return seq

        


