from flask import Flask
from flask_socketio import SocketIO, emit
import time
import threading

# -------------------------------------------------
# APP SETUP
# -------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hemesha-love'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# -------------------------------------------------
# GLOBAL STATE
# -------------------------------------------------

current_gesture = "NONE"
current_mode = "TREE"

hand_position = {
    "x": 0,
    "y": 0,
    "detected": False
}

photo_index = 0
auto_play_active = False

last_mode_change = 0
MODE_COOLDOWN = 0.5  # seconds

# -------------------------------------------------
# MODE UPDATE LOGIC
# -------------------------------------------------

def update_mode(gesture):
    global current_mode, auto_play_active, photo_index, last_mode_change

    now = time.time()
    if now - last_mode_change < MODE_COOLDOWN:
        return

    if gesture == "FIST":
        current_mode = "TREE"
        auto_play_active = False

    elif gesture == "OPEN":
        current_mode = "SCATTER"
        auto_play_active = False

    elif gesture == "PINCH":
        current_mode = "NEXT"
        photo_index += 1
        auto_play_active = False

    elif gesture == "PEACE":
        current_mode = "HEART"
        auto_play_active = False

    elif gesture == "THUMBS_UP":
        current_mode = "AUTOPLAY"
        auto_play_active = True

    last_mode_change = now

# -------------------------------------------------
# SOCKET.IO EVENTS
# -------------------------------------------------

@socketio.on("gesture_input")
def handle_gesture(data):
    """
    Expected data from frontend:
    {
        "gesture": "FIST | OPEN | PINCH | PEACE | THUMBS_UP",
        "hand": { "x": 0.1, "y": -0.3, "detected": true }
    }
    """
    global current_gesture, hand_position

    current_gesture = data.get("gesture", "NONE")
    hand_position = data.get("hand", hand_position)

    update_mode(current_gesture)

@socketio.on("connect")
def handle_connect():
    emit("gesture_update", {
        "gesture": current_gesture,
        "mode": current_mode,
        "hand": hand_position,
        "photoIndex": photo_index,
        "autoPlay": auto_play_active
    })

# -------------------------------------------------
# BACKGROUND UPDATE LOOP
# -------------------------------------------------

def background_updates():
    global photo_index
    last_auto = time.time()

    while True:
        if auto_play_active and time.time() - last_auto > 2.5:
            photo_index += 1
            last_auto = time.time()

        socketio.emit("gesture_update", {
            "gesture": current_gesture,
            "mode": current_mode,
            "hand": hand_position,
            "photoIndex": photo_index,
            "autoPlay": auto_play_active
        })

        time.sleep(0.033)  # ~30 FPS

# -------------------------------------------------
# ROUTES
# -------------------------------------------------

@app.route("/")
def index():
    return "🎄 Hemesha Christmas Gesture Backend – Railway Ready"

# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":
    print("=" * 55)
    print("   HEMESHA CHRISTMAS – RAILWAY BACKEND")
    print("   Made with ❤️ by Pahan Chethana")
    print("=" * 55)
    print(" Backend running successfully ")
    print("=" * 55)

    threading.Thread(
        target=background_updates,
        daemon=True
    ).start()

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=False
    )
