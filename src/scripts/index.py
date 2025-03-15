import time
import threading
import os, platform, subprocess, re
from datetime import date, datetime
from rgbmatrix import RGBMatrix, RGBMatrixOptions

# Mods Imports
from mods.clock import Clock
from mods.gifviewer import Gif
from mods.dvd import Dvd
from mods.test import PulsingColors
from mods.drawing import Drawing  # Import our new Drawing mode
from mods.ufc import UFCEvent
from flask import Flask, render_template, request, make_response, jsonify, redirect, url_for
import website.site
import shlex, subprocess
import psutil
import base64
import io
from PIL import Image

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
    uptime=getUptime(),
    matrix=matrix)
    
@app.route('/on', methods=['GET', 'POST'])
def on():
    # Turn on led panel
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
    # Turn off led panel
    print("Turning off")
    matrix.toggled = False
    matrix.run()
    data = {'message': 'Done', 'code': 'SUCCESS'}
    return make_response(jsonify(data), 201)

@app.route('/send-drawing', methods=['POST'])
def send_drawing():
    try:
        if request.method == 'POST':
            # Get the image data from the request
            image_data = request.form.get('image_data')
            
            # Check if we're in drawing mode
            if matrix.mode is None or not isinstance(matrix.mode, Drawing):
                # Switch to drawing mode
                matrix.toggled = True
                matrix.mode = Drawing(matrix.matrix)
                matrix.run()
            
            # Update the drawing
            success = matrix.mode.update_from_data_url(image_data)
            
            if success:
                return make_response(jsonify({'message': 'Drawing updated successfully'}), 200)
            else:
                return make_response(jsonify({'message': 'Failed to update drawing'}), 400)
    except Exception as e:
        print(f"Error in send_drawing: {e}")
        return make_response(jsonify({'message': f'Error: {str(e)}'}), 500)

@app.route('/system-info', methods=['GET'])
def system_info():
    """Return system information for AJAX updates"""
    return jsonify({
        'storage': getStorage(),
        'uptime': getUptime()
    })

def startWebsite():
    app.run(debug=True, use_reloader=False, host='192.168.1.217', port=8000)

def detect_model() -> str:
    try:
        with open('/proc/device-tree/model') as f:
            model = f.read()
        return model
    except:
        return "Unknown Model"

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
    try:
        cmd = "uptime -p"
        args = shlex.split(cmd)
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        return p.communicate()[0].decode("utf-8").strip().split(' ', 1)[1]
    except:
        return "Unknown"

if __name__ == "__main__":
    matrix = Matrix()
    start=datetime.now()
    
    # Use home directory for temporary files to avoid permission issues
    user_home = os.path.expanduser("~")
    print(f"Using home directory for file storage: {user_home}")
    
    startWebsite()