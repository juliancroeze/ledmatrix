from threading import Thread
from rgbmatrix import graphics
from mods.samplebase import SampleBase
import threading
import datetime

class Clock(SampleBase):
    def __init__(self, matrix):
        Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()

    def get_width(self, text):
        return len(text)*10

    def run(self):
        super(Clock, self).run()

        continuum = 0

        canvas = self.matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("../../fonts/10x20.bdf")

        while self.running:
            now = datetime.datetime.now()
            date_string = now.strftime('%Y-%m-%d')
            time = now.strftime("%H : %M : %S")

            continuum += 1
            continuum %= 3 * 255

            red = 0
            green = 0
            blue = 0

            if continuum <= 255:
                c = continuum
                blue = 255 - c
                red = c
            elif continuum > 255 and continuum <= 511:
                c = continuum - 256
                red = 255 - c
                green = c
            else:
                c = continuum - 512
                green = 255 - c
                blue = c

            canvas.Clear()
            graphics.DrawText(canvas, font, self.matrix.width/2 - (len(date_string)*10)/2, 25, graphics.Color(red, green, blue), date_string)
            graphics.DrawText(canvas, font, self.matrix.width/2 - (len(time)*10)/2, 50, graphics.Color(red, green, blue), time)

            graphics.DrawLine(canvas, 0, 0, 192, 0, graphics.Color(red, green, blue))
            graphics.DrawLine(canvas, 191, 0, 191, 63, graphics.Color(red, green, blue))
            graphics.DrawLine(canvas, 191, 63, 0, 63, graphics.Color(red, green, blue))
            graphics.DrawLine(canvas, 0, 0, 0, 63, graphics.Color(red, green, blue))
            canvas = self.matrix.SwapOnVSync(canvas)
        return True
        
        

