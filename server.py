from PIL import Image
from flask_pymongo import PyMongo
from bson.binary import Binary
import datetime
import threading
from time import sleep
import base64
import _pickle as cPickle
import numpy as np
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from playsound import playsound
import cv2


app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/myDatabase"
mongo = PyMongo(app)
db = mongo.db
cameras= db.cameras
cameras.delete_many({})
CORS(app)


def serializeFrame(frame):
    return Binary(cPickle.dumps(frame, protocol=2))

def addCamera(_id,name,background):
    global db
    global cameras
    camera = {"_id": _id,
            "name": name,
            "background": serializeFrame(background),
            "last_updated": datetime.datetime.utcnow()}
    cameras.insert_one(camera)


def processInitialFrame(image):
    gray_frame = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) #gray conversion
    return cv2.GaussianBlur(gray_frame,(25,25),0) #noise reduction


def base64ToImage(base64_string):   #transforms input base64_string into an image and crops out areas where movement will not occur
    imgdata = base64.b64decode(str(base64_string))
    image = Image.open(BytesIO(imgdata))  # left, up, right, bottom
    return np.array(image)


def convertToImage(base64_string):
    return processInitialFrame(base64ToImage(base64_string))


def saveIntruderImage(area,new,contour):
    filename = "./intruders/"+str(area)+".jpg"
    (x, y, w, h)=cv2.boundingRect(contour)
    cv2.rectangle(new, (x, y), (x+w, y+h), (0,255,0), 1)
    cv2.imwrite(filename, new)


def checkForIntruder(new,background):
    delta = cv2.absdiff(background,new)
    threshold = cv2.threshold(delta, 30, 255, cv2.THRESH_BINARY)[1]
    (contours,_)=cv2.findContours(threshold,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if(area > 20000):  #intruder detected
            saveIntruderImage(area,new,contour)
            return True

    return False

def soundAlarms():
     playsound('./alarm.mp3')

def thread_voice_alert(name):
    engine.say("Intruder Detected in \""+name+"\".")
    engine.runAndWait()


def updateBackground(frame,_id):
    global cameras
    filter = { "_id": _id }
    newBackground = { "$set": { "background": serializeFrame(frame),"last_updated": datetime.datetime.utcnow() } }
    cameras.update_one(filter,newBackground)


@app.route('/update', methods=['POST'])
def update_screencap():
    global cameras
    request_json = request.get_json()
    base64_string = request_json.get('base64_string')
    _id = request_json.get('_id')
    frame = convertToImage(base64_string)
    camera = cameras.find_one({'_id': _id})
    name = request_json.get('name')
    if camera is None:
        background = frame
        addCamera(_id,name,frame)
        print('Added new camera with name: \"'+ name +"\" to database.")
    else:
        background = cPickle.loads(camera['background'])
        last_updated = camera['last_updated']
        if(checkForIntruder(frame,background)):
            t = threading.Thread(target=soundAlarms)
            t.start()
            print("Intruder detected in "+name+"!")
            return jsonify(Intruder = True)
        seconds_passed = (datetime.datetime.utcnow() - last_updated).seconds  #seconds since background was last updated
        if( seconds_passed > 120):
            updateBackground(frame,_id)
            print('Background updated for camera: \"'+name+"\".")

    return jsonify(Intruder = False)
