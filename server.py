from PIL import Image
from PIL import ImageOps
from time import sleep
import base64
import numpy as np
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from playsound import playsound
import cv2


app = Flask(__name__)
CORS(app)
first = True


def processInitialFrame(image):
    gray_frame = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) #gray conversion
    return cv2.GaussianBlur(gray_frame,(25,25),0) #noise reduction


def base64ToImage(base64_string):   #transforms input base64_string into an image and crops out areas where movement will not occur
    imgdata = base64.b64decode(str(base64_string))
    image = ImageOps.crop(Image.open(BytesIO(imgdata)),(300,50,150, 50))  # left, up, right, bottom
    return np.array(image)


def convertToImage(base64_string):
    return processInitialFrame(base64ToImage(base64_string))


def saveIntruderImage(area,image):
    filename = str(area)+".jpg"
    (x, y, w, h)=cv2.boundingRect(contour)
    cv2.rectangle(new, (x, y), (x+w, y+h), (0,255,0), 1)
    cv2.imwrite(filename, new)


def checkForIntruder(new):
    global background

    delta = cv2.absdiff(background,new)
    threshold = cv2.threshold(delta, 30, 255, cv2.THRESH_BINARY)[1]
    (contours,_)=cv2.findContours(threshold,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if(area > 15000):  #intruder detected
            return True

    return False

def soundAlarms():
     playsound('./alarm.mp3')


@app.route('/update', methods=['POST'])
def update_screencap():
    global first
    global background
    request_json = request.get_json()
    base64_string = request_json.get('base64_string')
    frame = convertToImage(base64_string)
    if first:
        background = frame
        first = False
    else:
         if(checkForIntruder(frame)):
             soundAlarms()
             return jsonify(Intruder = True)

    return jsonify(Intruder = False)
