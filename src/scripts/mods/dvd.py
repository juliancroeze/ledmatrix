from mods.samplebase import SampleBase
from threading import Thread
from random import randint
import threading
from PIL import Image, ImageOps 
import time

class Dvd(SampleBase):
    def __init__(self, matrix):
        Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()
        self.winw = 192
        self.winh = 64

        self.width = 0
        self.height = 0

        self.addx = 1
        self.addy = 1

        self.oldColor = (255, 255, 255)

    def run(self):
        logo1 = Image.open("mods/images/ronalddvd.bmp").convert("RGB")
        # logo1 = ImageOps.colorize(logo1, white="blue", black="black")
        # logo1 = logo1.convert("RGB")

        self.height = logo1.height
        self.width = logo1.width

        posx = randint(0, self.winw - self.width - 2)
        posy = randint(0, self.winh - self.height - 2)

        def changeColor(img):
            pixels = img.load()
            for i in range(img.size[0]):
                for j in range(logo1.size[1]):
                    if pixels[i, j] == self.oldColor:
                        c = (0, randint(0, 255), 0)
                        pixels[i, j] = c
                        self.oldColor = c
                    


        while self.running:
            posx += self.addx
            posy += self.addy

            horizontal_hit = posx <= 0 or posx >= self.winw - self.width - 1
            vertical_hit = posy <= 0 or posy >= self.winh - self.height - 1
            
            if horizontal_hit:
                changeColor(logo1)
                self.addx *= -1
            if vertical_hit:
                
                changeColor(logo1)
                self.addy *= -1

            self.matrix.SetImage(logo1, posx, posy)
            time.sleep(0.05)
            self.matrix.Clear()


