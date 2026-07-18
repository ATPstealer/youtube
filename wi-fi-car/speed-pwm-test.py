#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import logging
import csv
import matplotlib.pyplot as plt

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =================================================================
# PIN DEFINITIONS (BCM numbering according to SCHEME.MD)
# =================================================================

# LEFT MOTOR
L_ENA = 12  # PWM
L_IN1 = 20
L_IN2 = 21

# RIGHT MOTOR
R_ENB = 13  # PWM
R_IN3 = 19
R_IN4 = 26

# ENCODERS
L_ENC_A = 14
L_ENC_B = 15
R_ENC_A = 17
R_ENC_B = 27

# =================================================================
# GLOBAL VARIABLES
# =================================================================

left_counter = 0
right_counter = 0
p_left = None
p_right = None

# =================================================================
# INTERRUPT HANDLERS
# =================================================================

def left_encoder_callback(channel):
    global left_counter
    left_counter += 1

def right_encoder_callback(channel):
    global right_counter
    right_counter += 1

# =================================================================
# GPIO CONTROL
# =================================================================

def setup():
    global p_left, p_right
    
    logging.info("Initializing GPIO...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Motors
    motor_pins = [L_ENA, L_IN1, L_IN2, R_ENB, R_IN3, R_IN4]
    for pin in motor_pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    # PWM
    p_left = GPIO.PWM(L_ENA, 1000)
    p_right = GPIO.PWM(R_ENB, 1000)
    p_left.start(0)
    p_right.start(0)

    # Encoders
    encoder_pins = [L_ENC_A, L_ENC_B, R_ENC_A, R_ENC_B]
    for pin in encoder_pins:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Interrupt registration (for maximum accuracy on both channels and both edges)
    GPIO.add_event_detect(L_ENC_A, GPIO.BOTH, callback=left_encoder_callback)
    GPIO.add_event_detect(L_ENC_B, GPIO.BOTH, callback=left_encoder_callback)
    GPIO.add_event_detect(R_ENC_A, GPIO.BOTH, callback=right_encoder_callback)
    GPIO.add_event_detect(R_ENC_B, GPIO.BOTH, callback=right_encoder_callback)
    
    logging.info("Initialization complete.")

def run_motors(speed):
    """Starts both motors forward with a given PWM speed"""
    speed = max(0, min(100, speed))
    
    # Left forward
    GPIO.output(L_IN1, GPIO.HIGH)
    GPIO.output(L_IN2, GPIO.LOW)
    p_left.ChangeDutyCycle(speed)
    
    # Right forward
    GPIO.output(R_IN3, GPIO.HIGH)
    GPIO.output(R_IN4, GPIO.LOW)
    p_right.ChangeDutyCycle(speed)

def stop_motors():
    p_left.ChangeDutyCycle(0)
    p_right.ChangeDutyCycle(0)
    GPIO.output(L_IN1, GPIO.LOW)
    GPIO.output(L_IN2, GPIO.LOW)
    GPIO.output(R_IN3, GPIO.LOW)
    GPIO.output(R_IN4, GPIO.LOW)

# =================================================================
# SPEED TEST
# =================================================================

def measure_speed(pwm_value, duration=2.0):
    global left_counter, right_counter
    
    logging.info(f"Testing PWM: {pwm_value}%")
    
    # Reset and acceleration
    stop_motors()
    time.sleep(0.5)
    run_motors(pwm_value)

    # Give 0.1 second for speed stabilization
    time.sleep(0.1)

    # Start measurement
    left_counter = 0
    right_counter = 0
    start_time = time.time()
    
    time.sleep(duration)
    
    end_time = time.time()
    stop_motors()
    
    dt = end_time - start_time
    # Calculate speed in ticks per second
    l_speed = left_counter / dt
    r_speed = right_counter / dt
    
    logging.info(f"Results for {pwm_value}%: Left={l_speed:.1f} tps, Right={r_speed:.1f} tps")
    return l_speed, r_speed

def main():
    setup()
    results = []
    # PWM range: from 1 to 100 with step 1 for a smoother graph
    pwm_values = range(1, 101, 1)
    
    try:
        logging.info("Starting test series...")
        for pwm in pwm_values:
            l_s, r_s = measure_speed(pwm)
            results.append({
                'pwm': pwm,
                'left_speed': round(l_s, 2),
                'right_speed': round(r_s, 2)
            })
            time.sleep(0.1) # Small break for motors
            
        # Write results to CSV
        filename = 'motor_speed_curve.csv'
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['pwm', 'left_speed', 'right_speed'])
            writer.writeheader()
            writer.writerows(results)
            
        logging.info(f"Testing complete. Data saved to {filename}")
        
        print("\nFinal table:")
        print("PWM (%) | Left (tps)  | Right (tps)")
        print("-" * 36)
        for res in results:
            print(f"{res['pwm']:7} | {res['left_speed']:11} | {res['right_speed']:12}")

        # Plotting graphs
        pwms = [r['pwm'] for r in results]
        left_speeds = [r['left_speed'] for r in results]
        right_speeds = [r['right_speed'] for r in results]

        plt.figure(figsize=(10, 6))
        plt.plot(pwms, left_speeds, label='Left motor', marker='o')
        plt.plot(pwms, right_speeds, label='Right motor', marker='s')
        plt.title('Speed vs PWM dependency')
        plt.xlabel('PWM (%)')
        plt.ylabel('Speed (tps)')
        plt.grid(True)
        plt.legend()
        
        plot_filename = 'motor_speed_curve.png'
        plt.savefig(plot_filename)
        logging.info(f"Graph saved to {plot_filename}")
        plt.show()

    except KeyboardInterrupt:
        logging.info("Test interrupted by user.")
    finally:
        stop_motors()
        GPIO.cleanup()
        logging.info("GPIO cleaned up.")

if __name__ == "__main__":
    main()
