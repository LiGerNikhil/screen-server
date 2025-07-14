# === Eventlet must be monkey patched before any other imports ===
import eventlet
eventlet.monkey_patch()

# === Standard & 3rd Party Imports ===
from flask import Flask, request
from flask_socketio import SocketIO, emit
import os
import base64
import cv2
import numpy as np
import time
import logging
from datetime import datetime

# === App Setup ===
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "your_secret_key")
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

# === Configuration ===
RESOLUTION = (1280, 720)

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

# === Global State ===
active_clients = {}

@app.route('/')
def index():
    return "🟢 Screen Server is Live"

@socketio.on('connect')
def handle_connect():
    logging.info("[+] Viewer connected")

@socketio.on('client_connected')
def client_connected(data):
    user = data.get("user", "unknown")
    active_clients[request.sid] = user
    logging.info(f"[+] Client connected: {user}")

@socketio.on('screen_data')
def handle_screen_data(data):
    user = data.get("user", "unknown")
    image = data.get("image", "")
    try:
        if process_frame(image):
            emit("screen_update", {"user": user, "image": image}, broadcast=True)
    except Exception as e:
        logging.error(f"[{user}] Frame error: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    user = active_clients.pop(sid, None)
    if user:
        logging.info(f"[-] Client disconnected: {user}")

# === Frame Processing ===
def process_frame(b64_img):
    try:
        if not b64_img:
            return False
        if b64_img.startswith('data:image'):
            b64_img = b64_img.split(',')[1]
        img_data = base64.b64decode(b64_img)
        np_arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return False
        if frame.shape[1] != RESOLUTION[0] or frame.shape[0] != RESOLUTION[1]:
            frame = cv2.resize(frame, RESOLUTION)
        return True
    except Exception as e:
        logging.error(f"[Frame Decode] Error: {e}")
        return False

# === Run Server ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
