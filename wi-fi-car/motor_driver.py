import RPi.GPIO as GPIO
import logging

class MotorDriver:
    def __init__(self, cfg):
        """cfg: the [motors] section of config.ini."""
        # Pin definitions (BCM)
        self.L_ENA, self.L_IN1, self.L_IN2 = cfg.getint('left_ena'), cfg.getint('left_in1'), cfg.getint('left_in2')
        self.R_ENB, self.R_IN3, self.R_IN4 = cfg.getint('right_enb'), cfg.getint('right_in3'), cfg.getint('right_in4')
        self.L_ENC_A, self.L_ENC_B = cfg.getint('left_enc_a'), cfg.getint('left_enc_b')
        self.R_ENC_A, self.R_ENC_B = cfg.getint('right_enc_a'), cfg.getint('right_enc_b')
        self.left_reverse = cfg.getboolean('left_reverse')
        self.right_reverse = cfg.getboolean('right_reverse')
        self.pwm_frequency = cfg.getint('pwm_frequency')

        # State initialization
        self.left_counter = 0
        self.right_counter = 0
        self.left_pos = 0
        self.right_pos = 0

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

        self.p_left = GPIO.PWM(self.L_ENA, self.pwm_frequency)
        self.p_right = GPIO.PWM(self.R_ENB, self.pwm_frequency)
        self.p_left.start(0)
        self.p_right.start(0)

        for pin in [self.L_ENC_A, self.L_ENC_B, self.R_ENC_A, self.R_ENC_B]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(self.L_ENC_A, GPIO.RISING, callback=self._left_encoder_callback)
        GPIO.add_event_detect(self.R_ENC_A, GPIO.RISING, callback=self._right_encoder_callback)

    def _left_encoder_callback(self, channel):
        if GPIO.input(self.L_ENC_B) == 0:
            self.left_pos += 1
        else:
            self.left_pos -= 1
        self.left_counter += 1

    def _right_encoder_callback(self, channel):
        if GPIO.input(self.R_ENC_B) == 0:
            self.right_pos += 1
        else:
            self.right_pos -= 1
        self.right_counter += 1

    def set_pwm(self, left, right):
        """
        Directly sets PWM for both motors.
        Values between -100 and 100. Positive = Forward, Negative = Backward.
        """
        self._set_motor(self.p_left, self.L_IN1, self.L_IN2, left, self.left_reverse)
        self._set_motor(self.p_right, self.R_IN3, self.R_IN4, right, self.right_reverse)

    @staticmethod
    def _set_motor(pwm, in_a, in_b, speed, reverse):
        speed = max(-100, min(100, speed))
        a_high = (speed >= 0) != reverse
        GPIO.output(in_a, GPIO.HIGH if a_high else GPIO.LOW)
        GPIO.output(in_b, GPIO.LOW if a_high else GPIO.HIGH)
        pwm.ChangeDutyCycle(abs(speed))

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
