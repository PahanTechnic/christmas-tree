from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit
import cv2
import mediapipe as mp
import numpy as np
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hemesha-love'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

current_gesture = "NONE"
current_mode = "TREE"
hand_position = {"x": 0, "y": 0, "detected": False}
gesture_history = []
GESTURE_HISTORY_SIZE = 5
last_mode_change = 0
MODE_COOLDOWN = 0.5
photo_index = 0
auto_play_active = False

camera = None
camera_lock = threading.Lock()

def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return camera

def detect_gesture(landmarks):
    global gesture_history, current_gesture, current_mode, last_mode_change
    global hand_position, photo_index, auto_play_active
    
    wrist = landmarks[0]
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    thumb_mcp = landmarks[2]
    index_tip = landmarks[8]
    index_pip = landmarks[6]
    middle_tip = landmarks[12]
    middle_pip = landmarks[10]
    ring_tip = landmarks[16]
    ring_pip = landmarks[14]
    pinky_tip = landmarks[20]
    pinky_pip = landmarks[18]
    middle_mcp = landmarks[9]
    
    hand_size = np.sqrt((middle_mcp.x - wrist.x)**2 + (middle_mcp.y - wrist.y)**2)
    if hand_size < 0.02:
        return "NONE"
    
    hand_position["x"] = (middle_mcp.x - 0.5) * 2
    hand_position["y"] = (middle_mcp.y - 0.5) * 2
    hand_position["detected"] = True
    
    def is_extended(tip, pip, wrist):
        return np.sqrt((tip.x-wrist.x)**2+(tip.y-wrist.y)**2) > np.sqrt((pip.x-wrist.x)**2+(pip.y-wrist.y)**2) * 1.15
    
    index_up = is_extended(index_tip, index_pip, wrist)
    middle_up = is_extended(middle_tip, middle_pip, wrist)
    ring_up = is_extended(ring_tip, ring_pip, wrist)
    pinky_up = is_extended(pinky_tip, pinky_pip, wrist)
    
    thumb_up = thumb_tip.y < thumb_mcp.y - 0.04
    thumb_extended = abs(thumb_tip.x - wrist.x) > abs(thumb_mcp.x - wrist.x) * 1.15
    
    extended_count = sum([index_up, middle_up, ring_up, pinky_up])
    
    pinch_dist = np.sqrt((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)
    pinch_ratio = pinch_dist / hand_size
    
    gesture = "NONE"
    
    # FIST - Christmas Tree
    if extended_count == 0 and not thumb_extended:
        gesture = "FIST"
    
    # OPEN - Scatter + Rotate + Random Preview
    elif extended_count >= 4:
        gesture = "OPEN"
    
    # PINCH - Next Photo
    elif pinch_ratio < 0.28 and extended_count <= 2:
        gesture = "PINCH"
    
    # PEACE - Heart + Hemesha Name
    elif index_up and middle_up and not ring_up and not pinky_up and not thumb_extended:
        gesture = "PEACE"
    
    # THUMBS UP - Auto Play
    elif thumb_up and not index_up and not middle_up and not ring_up and not pinky_up:
        gesture = "THUMBS_UP"
    
    gesture_history.append(gesture)
    if len(gesture_history) > GESTURE_HISTORY_SIZE:
        gesture_history.pop(0)
    
    gesture_counts = {}
    for g in gesture_history:
        gesture_counts[g] = gesture_counts.get(g, 0) + 1
    
    dominant = max(gesture_counts, key=gesture_counts.get) if gesture_counts else "NONE"
    current_gesture = dominant
    
    now = time.time()
    if now - last_mode_change > MODE_COOLDOWN:
        ct = 3
        
        if dominant == "FIST" and gesture_counts.get("FIST", 0) >= ct:
            if current_mode != "TREE":
                current_mode = "TREE"
                auto_play_active = False
                last_mode_change = now
                
        elif dominant == "OPEN" and gesture_counts.get("OPEN", 0) >= ct:
            if current_mode != "SCATTER":
                current_mode = "SCATTER"
                auto_play_active = False
                last_mode_change = now
                
        elif dominant == "PINCH" and gesture_counts.get("PINCH", 0) >= ct:
            current_mode = "NEXT"
            photo_index += 1
            auto_play_active = False
            last_mode_change = now
                
        elif dominant == "PEACE" and gesture_counts.get("PEACE", 0) >= ct:
            if current_mode != "HEART":
                current_mode = "HEART"
                auto_play_active = False
                last_mode_change = now
                
        elif dominant == "THUMBS_UP" and gesture_counts.get("THUMBS_UP", 0) >= ct:
            if current_mode != "AUTOPLAY":
                current_mode = "AUTOPLAY"
                auto_play_active = True
                last_mode_change = now
    
    return dominant

def generate_frames():
    global hand_position
    while True:
        with camera_lock:
            cam = get_camera()
            success, frame = cam.read()
        
        if not success:
            continue
        
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(255, 105, 180), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 215, 0), thickness=2)
                )
                detect_gesture(hand_landmarks.landmark)
        else:
            hand_position["detected"] = False
            gesture_history.clear()
        
        cv2.putText(frame, f"{current_gesture}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 105, 180), 2)
        cv2.putText(frame, f"{current_mode}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 215, 0), 2)
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def background_updates():
    global photo_index
    last_auto = time.time()
    while True:
        if auto_play_active and time.time() - last_auto > 2.5:
            photo_index += 1
            last_auto = time.time()
        
        socketio.emit('gesture_update', {
            'gesture': current_gesture,
            'mode': current_mode,
            'hand': hand_position,
            'photoIndex': photo_index,
            'autoPlay': auto_play_active
        })
        time.sleep(0.033)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect')
def handle_connect():
    emit('gesture_update', {
        'gesture': current_gesture,
        'mode': current_mode,
        'hand': hand_position,
        'photoIndex': photo_index,
        'autoPlay': auto_play_active
    })

if __name__ == '__main__':
    print("\n" + "="*55)
    print("        HEMESHA CHRISTMAS GIFT")
    print("        Made with Love by Pahan Chethana")
    print("="*55)
    print("\n  Open: http://localhost:5000\n")
    print("  GESTURES:")
    print("  " + "-"*45)
    print("  | FIST      | Christmas Tree             |")
    print("  | OPEN      | Scatter + Random Photo     |")
    print("  | PINCH     | Next Photo                 |")
    print("  | PEACE (V) | Heart + 'Hemesha' Name     |")
    print("  | THUMBS UP | Auto Play Slideshow        |")
    print("  " + "-"*45)
    print("\n" + "="*55 + "\n")
    
    threading.Thread(target=background_updates, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)