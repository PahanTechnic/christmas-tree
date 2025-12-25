from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import time
import threading
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hemesha-love-2025'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    ping_timeout=30,
    ping_interval=5
)

# ---------------- STATE ----------------
current_gesture = "NONE"
current_mode = "TREE"
hand_position = {"x": 0, "y": 0, "detected": False}
photo_index = 0
auto_play_active = False
last_mode_change = 0
MODE_COOLDOWN = 0.5

# ---------------- LOGIC ----------------
def update_mode(gesture):
    global current_mode, auto_play_active, photo_index, last_mode_change, current_gesture
    now = time.time()

    if now - last_mode_change < MODE_COOLDOWN:
        return

    current_gesture = gesture

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

# ---------------- SOCKET EVENTS ----------------
@socketio.on("gesture_input")
def on_gesture(data):
    gesture = data.get("gesture", "NONE")
    hand = data.get("hand", {"x": 0, "y": 0, "detected": False})
    hand_position.update(hand)
    update_mode(gesture)

@socketio.on("connect")
def on_connect():
    emit("gesture_update", {
        "gesture": current_gesture,
        "mode": current_mode,
        "hand": hand_position,
        "photoIndex": photo_index,
        "autoPlay": auto_play_active
    })

# ---------------- BACKGROUND LOOP ----------------
def background_loop():
    global photo_index, last_auto
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
        }, broadcast=True)

        socketio.sleep(0.033)

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("=" * 55)
    print(" HEMESHA CHRISTMAS – RAILWAY READY ❤️ ")
    print(" Made with ❤️ by Pahan Chethana ")
    print("=" * 55)

    threading.Thread(target=background_loop, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
