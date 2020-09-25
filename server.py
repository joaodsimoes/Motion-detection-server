from PIL import Image
from PIL import ImageOps
from time import sleep
import base64
import numpy as np
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from skimage import measure
from playsound import playsound

app = Flask(__name__)
CORS(app)
first = True



def base64ToImage(base64_string):
    imgdata = base64.b64decode(str(base64_string))
    image = ImageOps.crop(Image.open(BytesIO(imgdata)),(300,50,150, 50))  # left, up, right, bottom
    return np.array(image)

def checkForIntruder(new):
    global background
    diff = measure.compare_ssim(background, new,multichannel=True)
    print(diff)
    if(diff < 0.93):
        #print("intruso")
        playsound('./alarm.mp3')
        sleep(4)
    elif( diff < 0.96):
        background = new
        print("Refreshed background.")

@app.route('/update', methods=['POST'])
def update_screencap():
    global first
    global background
    request_json = request.get_json()
    base64_string = request_json.get('base64_string')
    if first:
        background = base64ToImage(base64_string)
        first = False
    else:
         checkForIntruder(base64ToImage(base64_string))

    return 'OK'
