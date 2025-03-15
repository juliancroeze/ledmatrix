from flask import Flask, render_template, request
import threading
import index
app = Flask(__name__)

@app.route('/on')
def on():
    #turn on led panel
    index.toggled = True
    return render_template('on.html')

@app.route('/off')
def off():
    #turn off led panel
    index.toggled = False
    return render_template('off.html')

def web():
    app.run(debug=True, use_reloader=False, host='192.168.1.217')

def startWebsite():
    threading.Thread(target=web).start()


