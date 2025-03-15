import time
import threading
import os, platform, subprocess, re
from datetime import date, datetime
from rgbmatrix import RGBMatrix, RGBMatrixOptions

#Mods Imports
from mods.clock import Clock
from mods.gifviewer import Gif
from mods.dvd import Dvd
from mods.test import PulsingColors
from flask import Flask, render_template, request, make_response, jsonify, redirect
import website.site
import shlex, subprocess
import psutil



class Matrix(): 
    def __init__(self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 6
        options.parallel = 2
        options.pixel_mapper_config = "U-mapper"
        options.show_refresh_rate = 0
        options.gpio_slowdown = 4
        options.led_rgb_sequence = "RBG"
        options.pwm_lsb_nanoseconds = 500
        options.pwm_bits = 8
        self.toggled = False
        self.mode = None
        self.matrix = RGBMatrix(options = options)
        self.modes = []

    def run(self):        
        if self.toggled:
            if self.mode != None:
                self.mode.process()
        else:
            if self.mode != None:
                self.mode.kill()
                self.matrix.Clear()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    test()
    return render_template(
    'index.html',
    data=[{'name':'dvd'}, {'name':'gif'}, {'name':'clock'}, {'name':'test'}],
    model=detect_model(),
    storage=getStorage(),
    uptime=getUptime())
    
@app.route('/on', methods=['GET', 'POST'])
def on():
    #turn on led panel
    matrix.toggled = True
    selected = request.form.get('comp_select')
    if selected == 'clock':
        matrix.mode = Clock(matrix.matrix)
    if selected == 'gif':
        matrix.mode = Gif(matrix.matrix)
    if selected == 'dvd':
        matrix.mode = Dvd(matrix.matrix)
    if selected == 'test':
        matrix.mode = PulsingColors(matrix.matrix)
    matrix.run()
    return redirect('/')

@app.route('/off', methods=['GET', 'POST'])
def off():
    #turn off led panel
    print("Turning off")
    matrix.toggled = False
    matrix.run()
    data = {'message': 'Done', 'code': 'SUCCESS'}
    return make_response(jsonify(data), 201)

def startWebsite():
    app.run(debug=True, use_reloader=False, host='192.168.1.217', port=8000)

def detect_model() -> str:
    with open('/proc/device-tree/model') as f:
        model = f.read()
    return model

def test():
        # Get cpu statistics
    cpu = str(psutil.cpu_percent()) + '%'

    # Calculate memory information
    memory = psutil.virtual_memory()
    # Convert Bytes to MB (Bytes -> KB -> MB)
    available = round(memory.available/1024.0/1024.0,1)
    total = round(memory.total/1024.0/1024.0,1)
    mem_info = str(available) + 'MB free / ' + str(total) + 'MB total ( ' + str(memory.percent) + '% )'

    # Calculate disk information
    disk = psutil.disk_usage('/')
    # Convert Bytes to GB (Bytes -> KB -> MB -> GB)
    free = round(disk.free/1024.0/1024.0/1024.0,1)
    total = round(disk.total/1024.0/1024.0/1024.0,1)
    disk_info = str(free) + 'GB free / ' + str(total) + 'GB total ( ' + str(disk.percent) + '% )'

    print("CPU Info–> ", cpu)
    print("Memory Info–>", mem_info)
    print("Disk Info–>", disk_info)
        
def getStorage() -> str:
    disk = psutil.disk_usage('/')

    free = round(disk.free/1024.0/1024.0/1024.0,1)
    total = round(disk.total/1024.0/1024.0/1024.0,1)
    return str(free) + 'GB free / ' + str(total) + 'GB total ( ' + str(disk.percent) + '% )'

def getUptime() -> str:
    cmd = "uptime -p"
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    return p.communicate()[0].decode("utf-8").strip().split(' ', 1)[1]

if __name__ == "__main__":
    matrix = Matrix()
    start=datetime.now()
    startWebsite()

