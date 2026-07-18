import RPi.GPIO as GPIO
import logging

class MotorDriver:
    def __init__(self):
        # Pin definitions (BCM)
        self.L_ENA, self.L_IN1, self.L_IN2 = 12, 20, 21
        self.R_ENB, self.R_IN3, self.R_IN4 = 13, 19, 26
        self.L_ENC_A, self.L_ENC_B = 14, 15
        self.R_ENC_A, self.R_ENC_B = 17, 27

        # State initialization
        self.left_counter = 0
        self.right_counter = 0
        self.left_pos = 0
        self.right_pos = 0
        self.left_last_state = 0
        self.right_last_state = 0

        self.transitions = {
            (0b00, 0b01): 1, (0b01, 0b11): 1, (0b11, 0b10): 1, (0b10, 0b00): 1,
            (0b00, 0b10): -1, (0b10, 0b11): -1, (0b11, 0b01): -1, (0b01, 0b00): -1,
        }

        self.p_left = None
        self.p_right = None

        self._setup_gpio()

    def _setup_gpio(self):
        """Internal method to initialize GPIO pins and PWM."""
        logging.info("Initializing GPIO in MotorDriver class...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in [self.L_ENA, self.L_IN1, self.L_IN2, self.R_ENB, self.R_IN3, self.R_IN4]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

        self.p_left = GPIO.PWM(self.L_ENA, 1000)
        self.p_right = GPIO.PWM(self.R_ENB, 1000)
        self.p_left.start(0)
        self.p_right.start(0)

        for pin in [self.L_ENC_A, self.L_ENC_B, self.R_ENC_A, self.R_ENC_B]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.left_last_state = (GPIO.input(self.L_ENC_A) << 1) | GPIO.input(self.L_ENC_B)
        self.right_last_state = (GPIO.input(self.R_ENC_A) << 1) | GPIO.input(self.R_ENC_B)

        GPIO.add_event_detect(self.L_ENC_A, GPIO.BOTH, callback=self._left_encoder_callback)
        GPIO.add_event_detect(self.L_ENC_B, GPIO.BOTH, callback=self._left_encoder_callback)
        GPIO.add_event_detect(self.R_ENC_A, GPIO.BOTH, callback=self._right_encoder_callback)
        GPIO.add_event_detect(self.R_ENC_B, GPIO.BOTH, callback=self._right_encoder_callback)

    def _left_encoder_callback(self, channel):
        a = GPIO.input(self.L_ENC_A)
        b = GPIO.input(self.L_ENC_B)
        current_state = (a << 1) | b
        if current_state != self.left_last_state:
            transition = (self.left_last_state, current_state)
            if transition in self.transitions:
                self.left_pos += self.transitions[transition]
                self.left_counter += 1
            self.left_last_state = current_state

    def _right_encoder_callback(self, channel):
        a = GPIO.input(self.R_ENC_A)
        b = GPIO.input(self.R_ENC_B)
        current_state = (a << 1) | b
        if current_state != self.right_last_state:
            transition = (self.right_last_state, current_state)
            if transition in self.transitions:
                self.right_pos += self.transitions[transition]
                self.right_counter += 1
            self.right_last_state = current_state

    def set_pwm(self, left, right):
        """
        Directly sets PWM for both motors.
        Values between -100 and 100. Positive = Forward, Negative = Backward.
        """
        # Left Motor
        l_speed = max(-100, min(100, left))
        if l_speed >= 0:
            GPIO.output(self.L_IN1, GPIO.LOW)
            GPIO.output(self.L_IN2, GPIO.HIGH)
            self.p_left.ChangeDutyCycle(l_speed)
        else:
            GPIO.output(self.L_IN1, GPIO.HIGH)
            GPIO.output(self.L_IN2, GPIO.LOW)
            self.p_left.ChangeDutyCycle(-l_speed)

        # Right Motor
        r_speed = max(-100, min(100, right))
        if r_speed >= 0:
            GPIO.output(self.R_IN3, GPIO.HIGH)
            GPIO.output(self.R_IN4, GPIO.LOW)
            self.p_right.ChangeDutyCycle(r_speed)
        else:
            GPIO.output(self.R_IN3, GPIO.LOW)
            GPIO.output(self.R_IN4, GPIO.HIGH)
            self.p_right.ChangeDutyCycle(-r_speed)

    def stop(self):
        """Stops both motors."""
        if self.p_left: self.p_left.ChangeDutyCycle(0)
        if self.p_right: self.p_right.ChangeDutyCycle(0)
        for pin in [self.L_IN1, self.L_IN2, self.R_IN3, self.R_IN4]:
            GPIO.output(pin, GPIO.LOW)

    def get_encoders(self):
        """Returns current encoder counts (Left, Right)."""
        return self.left_counter, self.right_counter

    def reset_encoders(self):
        """Resets all encoder counters and positions."""
        self.left_counter = 0
        self.right_counter = 0
        self.left_pos = 0
        self.right_pos = 0
