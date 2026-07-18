#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import sys
import logging

# Logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =================================================================
# PIN DEFINITIONS (BCM numbering)
# =================================================================

# LEFT MOTOR (P4)
L_ENA = 12  # pin 32 (PWM)
L_IN1 = 20  # pin 38
L_IN2 = 21  # pin 40

# RIGHT MOTOR (P3)
R_ENB = 13  # pin 33 (PWM)
R_IN3 = 19  # pin 35
R_IN4 = 26  # pin 37

# LEFT ENCODER
L_ENC_A = 14  # pin 8
L_ENC_B = 15  # pin 10

# RIGHT ENCODER
R_ENC_A = 17  # pin 11
R_ENC_B = 27  # pin 13

# =================================================================
# GLOBAL VARIABLES
# =================================================================

left_counter = 0
right_counter = 0
left_pos = 0
right_pos = 0
left_last_state = 0
right_last_state = 0

transitions = {
    (0b00, 0b01): 1,
    (0b01, 0b11): 1,
    (0b11, 0b10): 1,
    (0b10, 0b00): 1,

    (0b00, 0b10): -1,
    (0b10, 0b11): -1,
    (0b11, 0b01): -1,
    (0b01, 0b00): -1,
}

p_left = None
p_right = None
test_results = []  # List for final report

# =================================================================
# ENCODER INTERRUPT HANDLERS
# =================================================================

def left_encoder_callback(channel):
    global left_counter, left_pos, left_last_state
    
    a = GPIO.input(L_ENC_A)
    b = GPIO.input(L_ENC_B)
    current_state = (a << 1) | b
    
    if current_state != left_last_state:
        transition = (left_last_state, current_state)
        if transition in transitions:
            left_pos += transitions[transition]
            left_counter += 1
        left_last_state = current_state
        logging.debug(f"LEFT encoder: counter={left_counter}, pos={left_pos}")

def right_encoder_callback(channel):
    global right_counter, right_pos, right_last_state
    
    a = GPIO.input(R_ENC_A)
    b = GPIO.input(R_ENC_B)
    current_state = (a << 1) | b
    
    if current_state != right_last_state:
        transition = (right_last_state, current_state)
        if transition in transitions:
            right_pos += transitions[transition]
            right_counter += 1
        right_last_state = current_state
        logging.debug(f"RIGHT encoder: counter={right_counter}, pos={right_pos}")


# =================================================================
# GPIO SETUP
# =================================================================

def setup():
    global p_left, p_right
    
    logging.info("Initializing GPIO...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Motor control pins setup
    motor_pins = [L_ENA, L_IN1, L_IN2, R_ENB, R_IN3, R_IN4]
    for pin in motor_pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    # PWM setup for speed
    p_left = GPIO.PWM(L_ENA, 1000)   # 1 kHz frequency
    p_right = GPIO.PWM(R_ENB, 1000)  # 1 kHz frequency
    p_left.start(0)
    p_right.start(0)

    # Encoder pins setup
    encoder_pins = [L_ENC_A, L_ENC_B, R_ENC_A, R_ENC_B]
    for pin in encoder_pins:
        # Use internal pull-up
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Initial encoder state
    global left_last_state, right_last_state
    left_last_state = (GPIO.input(L_ENC_A) << 1) | GPIO.input(L_ENC_B)
    right_last_state = (GPIO.input(R_ENC_A) << 1) | GPIO.input(R_ENC_B)

    # Interrupt registration for both A and B channels in BOTH mode.
    GPIO.add_event_detect(L_ENC_A, GPIO.BOTH, callback=left_encoder_callback)
    GPIO.add_event_detect(L_ENC_B, GPIO.BOTH, callback=left_encoder_callback)
    GPIO.add_event_detect(R_ENC_A, GPIO.BOTH, callback=right_encoder_callback)
    GPIO.add_event_detect(R_ENC_B, GPIO.BOTH, callback=right_encoder_callback)
    
    logging.info("Initialization complete.")

# run('l/r', 'f/b', 'speed(0-100)')
def run(motor, direction, speed):
    speed = max(0, min(100, speed))

    if motor == 'l':
        if direction == 'f':
            GPIO.output(L_IN1, GPIO.HIGH)
            GPIO.output(L_IN2, GPIO.LOW)
        elif direction == 'b':
            GPIO.output(L_IN1, GPIO.LOW)
            GPIO.output(L_IN2, GPIO.HIGH)
        else:
            logging.error("direction must be 'forward' or 'backward'")
            return

        p_left.ChangeDutyCycle(speed)

    elif motor == 'r':
        if direction == 'f':
            GPIO.output(R_IN3, GPIO.HIGH)
            GPIO.output(R_IN4, GPIO.LOW)
        elif direction == 'b':
            GPIO.output(R_IN3, GPIO.LOW)
            GPIO.output(R_IN4, GPIO.HIGH)
        else:
            logging.error("direction must be 'forward' or 'backward'")
            return

        p_right.ChangeDutyCycle(speed)

    else:
        logging.error("motor must be 'left' or 'right'")

def stop():
    p_left.ChangeDutyCycle(0)
    p_right.ChangeDutyCycle(0)

    GPIO.output(L_IN1, GPIO.LOW)
    GPIO.output(L_IN2, GPIO.LOW)
    GPIO.output(R_IN3, GPIO.LOW)
    GPIO.output(R_IN4, GPIO.LOW)


setup()
run('r', 'f', 20)
time.sleep(1)
left_counter = 0
right_counter = 0
left_pos = 0
right_pos = 0
time.sleep(2)

stop()