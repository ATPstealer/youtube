import argparse
import motor_driver
import car_controller
import camera_driver
import time
import logging
import RPi.GPIO as GPIO
from flask import Flask, render_template, Response, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Global instances
driver = None
controller = None
cam = None

def get_cam():
    global cam
    if cam is None:
        cam = camera_driver.CameraDriver()
    return cam

def gen_frames():
    """Generator for the video stream."""
    camera = get_cam()
    while True:
        frame = camera.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.1)

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control', methods=['POST'])
def control():
    """Control API for movement."""
    global controller
    data = request.get_json()
    action = data.get('action') # 'move', 'turn' or 'stop'
    speed = int(data.get('speed', 0))
    direction = data.get('direction', 'f')
    
    if action == 'stop' or speed == 0:
        controller.stop()
        logging.info("Web Control: Stop")
    elif action == 'turn':
        # direction here is 'l' or 'r'
        controller.turn(speed, direction)
    else:
        controller.drive(speed, direction)
        logging.info(f"Web Control: Drive {direction} at {speed}%")
        
    return jsonify({'status': 'ok'})

def test_camera():
    """Verify the camera driver is working."""
    logging.info("Testing camera driver...")
    cam = camera_driver.CameraDriver()
    frame = cam.get_frame()
    if frame:
        logging.info(f"Successfully captured a frame of size {len(frame)} bytes.")
    else:
        logging.error("Failed to capture a frame.")

def main():
    global driver, controller
    
    parser = argparse.ArgumentParser(description='Wi-Fi Car Control and Testing')
    parser.add_argument('--test-camera', action='store_true', help='Verify camera capture')
    parser.add_argument('--port', type=int, default=5000, help='Port for web server (default: 5000)')
    
    args = parser.parse_args()

    if args.test_camera:
        test_camera()
    else:
        logging.info(f"Starting web server on port {args.port}...")
        driver = motor_driver.MotorDriver()
        controller = car_controller.CarController(driver)
        try:
            app.run(host='0.0.0.0', port=args.port, threaded=True)
        finally:
            controller.stop()
            GPIO.cleanup()
            logging.info("Cleaned up on exit.")

if __name__ == "__main__":
    main()
