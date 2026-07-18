import argparse
import collections
import threading
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

# Web log buffer
log_buffer = collections.deque(maxlen=50)

class WebLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        log_buffer.append(log_entry)

web_handler = WebLogHandler()
web_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(web_handler)

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
    global controller, driver
    data = request.get_json()
    action = data.get('action') # 'move', 'turn' or 'stop'
    speed = int(data.get('speed', 0))
    direction = data.get('direction', 'f')
    
    l_enc, r_enc = driver.get_encoders() if driver else (0, 0)
    
    if action == 'stop' or speed == 0:
        controller.stop()
        logging.info(f"Web Control: Stop | Encoders: L={l_enc}, R={r_enc}")
    elif action == 'turn':
        # direction here is 'l' or 'r'
        controller.turn(speed, direction)
        logging.info(f"Web Control: Turn {direction} at {speed}% | Encoders: L={l_enc}, R={r_enc}")
    else:
        controller.drive(speed, direction)
        logging.info(f"Web Control: Drive {direction} at {speed}% | Encoders: L={l_enc}, R={r_enc}")
        
    return jsonify({'status': 'ok'})

@app.route('/logs')
def get_logs():
    """Returns the last N log entries as JSON."""
    return jsonify(list(log_buffer))

def test_camera():
    """
    Iteration 5.1: Verifying the camera driver.
    """
    logging.info("Testing camera driver...")
    cam = camera_driver.CameraDriver()
    frame = cam.get_frame()
    if frame:
        logging.info(f"Successfully captured a frame of size {len(frame)} bytes.")
    else:
        logging.error("Failed to capture a frame.")

def test_motor_speed(step):
    """
    Step 5: Extended motor speed test with custom discretization step.
    Measures TPS for both motors across a range of PWM values.
    """
    logging.info(f"Starting extended motor speed test (Step={step})")
    
    driver = motor_driver.MotorDriver()
    results = []
    
    try:
        # PWM range from 'step' to 100
        pwm_values = range(step, 101, step)
        
        for pwm in pwm_values:
            logging.info(f"Measuring characteristics for {pwm}% PWM...")
            
            # Reset and small rest
            driver.stop()
            time.sleep(0.5)
            
            # Start motors
            driver.set_pwm(pwm, pwm)
            # Short stabilization period
            time.sleep(0.2)
            
            # Start measurement
            driver.reset_encoders()
            start_time = time.time()
            time.sleep(2.0) # Measure for 2 seconds
            end_time = time.time()
            
            driver.stop()
            
            # Calculate TPS
            l_cnt, r_cnt = driver.get_encoders()
            duration = end_time - start_time
            l_tps = l_cnt / duration
            r_tps = r_cnt / duration
            
            results.append({
                'pwm': pwm,
                'l_tps': l_tps,
                'r_tps': r_tps
            })
            
            logging.info(f"Result: L={l_tps:.1f} tps, R={r_tps:.1f} tps")
            
        # Output final table
        print("\n" + "="*40)
        print(" MOTOR CALIBRATION TABLE")
        print("="*40)
        print(" PWM (%) | Left (tps) | Right (tps)")
        print("-" * 40)
        for res in results:
            print(f" {res['pwm']:7} | {res['l_tps']:10.2f} | {res['r_tps']:11.2f}")
        print("-" * 40)
        print("Test completed successfully.")
        
    except KeyboardInterrupt:
        logging.info("Test interrupted by user.")
    finally:
        driver.stop()
        GPIO.cleanup()
        logging.info("GPIO cleaned up.")

def status_logger():
    """Background thread to log encoder and PWM values periodically."""
    global driver, controller
    while True:
        try:
            if driver and controller:
                l_enc, r_enc = driver.get_encoders()
                l_pwm = controller.current_l_pwm
                r_pwm = controller.current_r_pwm
                logging.info(f"FULL STATUS: Encoders L={l_enc}, R={r_enc} | PWM L={l_pwm}, R={r_pwm}")
        except Exception as e:
            logging.error(f"Error in status_logger: {e}")
        time.sleep(5.0)

def main():
    global driver, controller
    
    parser = argparse.ArgumentParser(description='Wi-Fi Car Control and Testing')
    parser.add_argument('--test-motor-speed', type=int, help='Run motor speed test with given step (e.g. 10)')
    parser.add_argument('--test-camera', action='store_true', help='Verify camera capture')
    parser.add_argument('--port', type=int, default=5000, help='Port for web server (default: 5000)')
    
    args = parser.parse_args()

    if args.test_motor_speed is not None:
        test_motor_speed(args.test_motor_speed)
    elif args.test_camera:
        test_camera()
    else:
        logging.info(f"Starting web server on port {args.port}...")
        driver = motor_driver.MotorDriver()
        controller = car_controller.CarController(driver)
        
        # Start background status logger
        threading.Thread(target=status_logger, daemon=True).start()
        
        try:
            app.run(host='0.0.0.0', port=args.port, threaded=True)
        finally:
            controller.stop()
            GPIO.cleanup()
            logging.info("Cleaned up on exit.")

if __name__ == "__main__":
    main()
