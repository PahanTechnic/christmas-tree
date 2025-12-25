from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import time
import threading
import cv2
import os  # අලුතෙන් import කරන්න

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hemesha-love'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# ---------------- STATE ----------------
current_gesture = "NONE"
current_mode = "TREE"
hand_position = {"x": 0, "y": 0, "detected": False}
photo_index = 0
auto_play_active = False
last_mode_change = 0
MODE_COOLDOWN = 0.5

# ---------------- CAMERA SETUP ----------------
def generate_camera_feed():
    """Camera feed generator for web display"""
    try:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        while True:
            success, frame = camera.read()
            if not success:
                break
            
            # Convert frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    except Exception as e:
        print(f"Camera error: {e}")
        # Fallback black frame
        black_frame = b'\xff' * (640 * 480 * 3)
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + black_frame + b'\r\n')

# ---------------- LOGIC ----------------
def update_mode(gesture):
    global current_mode, auto_play_active, photo_index, last_mode_change
    now = time.time()

    if now - last_mode_change < MODE_COOLDOWN:
        return

    if gesture == "FIST":
        current_mode = "TREE"
        auto_play_active = False
        print("Mode changed: TREE")

    elif gesture == "OPEN":
        current_mode = "SCATTER"
        auto_play_active = False
        print("Mode changed: SCATTER")

    elif gesture == "PINCH":
        current_mode = "NEXT"
        photo_index += 1
        auto_play_active = False
        print(f"Mode changed: NEXT (Photo: {photo_index})")

    elif gesture == "PEACE":
        current_mode = "HEART"
        auto_play_active = False
        print("Mode changed: HEART")

    elif gesture == "THUMBS_UP":
        current_mode = "AUTOPLAY"
        auto_play_active = True
        print("Mode changed: AUTOPLAY")

    last_mode_change = now

# ---------------- SOCKET EVENTS ----------------
@socketio.on("gesture_input")
def on_gesture(data):
    global current_gesture, hand_position
    current_gesture = data.get("gesture", "NONE")
    hand_position = data.get("hand", hand_position)
    update_mode(current_gesture)
    
    print(f"Gesture received: {current_gesture}")
    
    # Broadcast to all clients
    emit("gesture_update", {
        "gesture": current_gesture,
        "mode": current_mode,
        "hand": hand_position,
        "photoIndex": photo_index,
        "autoPlay": auto_play_active
    }, broadcast=True)

@socketio.on("connect")
def on_connect():
    print("Client connected")
    emit("gesture_update", {
        "gesture": current_gesture,
        "mode": current_mode,
        "hand": hand_position,
        "photoIndex": photo_index,
        "autoPlay": auto_play_active
    })

# ---------------- BACKGROUND LOOP ----------------
def background_loop():
    global photo_index
    last_auto = time.time()

    while True:
        if auto_play_active and time.time() - last_auto > 2.5:
            photo_index += 1
            last_auto = time.time()
            print(f"Auto-play: Photo index {photo_index}")

        socketio.emit("gesture_update", {
            "gesture": current_gesture,
            "mode": current_mode,
            "hand": hand_position,
            "photoIndex": photo_index,
            "autoPlay": auto_play_active
        })

        time.sleep(0.033)  # ~30 FPS

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    """Video streaming route for webcam"""
    return Response(generate_camera_feed(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/test")
def test():
    """Test route for Railway deployment check"""
    return {
        "status": "online",
        "message": "Hemesha Christmas App is running!",
        "modes": ["TREE", "SCATTER", "HEART", "AUTOPLAY"],
        "gestures": ["FIST", "OPEN", "PINCH", "PEACE", "THUMBS_UP"]
    }

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("=" * 55)
    print(" HEMESHA CHRISTMAS – RAILWAY READY ")
    print(" Made with ❤️ by Pahan Chethana ")
    print("=" * 55)
    print("\nAvailable gestures:")
    print("✊ FIST        = Christmas Tree")
    print("✋ OPEN        = Scatter + Photo")
    print("🤏 PINCH       = Next Photo")
    print("✌️ PEACE       = Heart + Name")
    print("👍 THUMBS_UP   = Auto Slideshow")
    print("\nServer starting...")

    # Start background thread
    threading.Thread(target=background_loop, daemon=True).start()

    # Railway සඳහා port environment variable එක භාවිතා කරන්න
    port = int(os.environ.get("PORT", 5000))
    
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
