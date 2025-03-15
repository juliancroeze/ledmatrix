from threading import Thread
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))

class SampleBase(Thread):
    def __init__(self, matrix):
        super(SampleBase, self).__init__()
        self.matrix = matrix
        self.running = False

    def usleep(self, value):
        time.sleep(value / 1000000.0)

    def run(self):
        return True

    def process(self):
        self.running = True
        self.start()

        return True

    def kill(self):
        self.running = False
        self.join()
