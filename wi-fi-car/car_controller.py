import logging
import time

class CarController:
    def __init__(self, driver):
        self.driver = driver
        # Approximate maximum Ticks Per Second from SPEED.MD (at 100% PWM)
        self.max_tps = 4600.0
        
        # Calibration data points from SPEED.MD: PWM -> (Left TPS, Right TPS)
        # Using a subset of points for efficient interpolation
        self.calibration_points = {
            14: (728.47, 835.47),
            20: (1458.94, 1425.44),
            30: (2284.41, 2308.41),
            40: (2897.33, 2938.33),
            50: (3346.37, 3416.86),
            60: (3636.32, 3742.81),
            70: (3900.34, 3972.34),
            80: (4081.35, 4145.34),
            90: (4262.82, 4339.32),
            100: (4582.32, 4685.32)
        }

    def get_pwms_for_speed(self, speed_pct):
        """
        Maps desired speed percentage (0-100%) to specific PWM values 
        for Left and Right motors based on calibration data.
        """
        if speed_pct <= 0:
            return 0.0, 0.0
        
        target_tps = (speed_pct / 100.0) * self.max_tps
        
        l_pwm = self._interpolate_pwm(target_tps, 'l')
        r_pwm = self._interpolate_pwm(target_tps, 'r')
        
        return round(l_pwm, 1), round(r_pwm, 1)

    def drive(self, speed_pct, direction='f'):
        """
        Drives the car at a logical speed percentage.
        direction: 'f' for forward, 'b' for backward.
        """
        l_pwm, r_pwm = self.get_pwms_for_speed(speed_pct)
        
        if direction == 'b':
            l_pwm = -l_pwm
            r_pwm = -r_pwm
            
        logging.info(f"Driving {direction} at {speed_pct}% speed (L_PWM={l_pwm}, R_PWM={r_pwm})")
        self.driver.set_pwm(l_pwm, r_pwm)

    def turn(self, speed_pct, side):
        """
        Turns the car in place.
        side: 'l' for left, 'r' for right.
        """
        l_pwm, r_pwm = self.get_pwms_for_speed(speed_pct)
        if side == 'l':
            logging.info(f"Turning Left at {speed_pct}%")
            self.driver.set_pwm(-l_pwm, r_pwm)
        else:
            logging.info(f"Turning Right at {speed_pct}%")
            self.driver.set_pwm(l_pwm, -r_pwm)

    def stop(self):
        """Stops the car."""
        self.driver.stop()

    def drive_stabilized(self, speed_pct, duration, direction='f'):
        """
        Drives the car straight by compensating for motor differences using encoders.
        If one motor is faster (higher encoder count), its PWM is reduced.
        Then it gradually grows back to the base value when leveled.
        """
        l_base, r_base = self.get_pwms_for_speed(speed_pct)
        l_curr, r_curr = l_base, r_base
        
        sign = 1 if direction == 'f' else -1
        
        self.driver.reset_encoders()
        self.driver.set_pwm(l_curr * sign, r_curr * sign)
        
        start_time = time.time()
        check_interval = 0.1   # 100ms
        diff_threshold = 20    # tick difference to trigger correction
        correction_step = 1.0  # PWM units to decrease
        growth_step = 0.5      # PWM units to grow back
        
        logging.info(f"Starting stabilized drive: {speed_pct}% for {duration}s")
        
        try:
            while time.time() - start_time < duration:
                time.sleep(check_interval)
                l_enc, r_enc = self.driver.get_encoders()
                
                diff = l_enc - r_enc
                
                if diff > diff_threshold:
                    # Left is ahead, reduce its PWM
                    l_curr -= correction_step
                elif diff < -diff_threshold:
                    # Right is ahead, reduce its PWM
                    r_curr -= correction_step
                else:
                    # Within threshold, gradually return to base PWM
                    if l_curr < l_base:
                        l_curr += growth_step
                    if r_curr < r_base:
                        r_curr += growth_step
                
                # Clamp to [0, base]
                l_curr = max(0, min(l_curr, l_base))
                r_curr = max(0, min(r_curr, r_base))
                
                self.driver.set_pwm(l_curr * sign, r_curr * sign)
                
                # Optional: log status every second
                if int((time.time() - start_time) * 10) % 10 == 0:
                     logging.info(f"Encoders: L={l_enc}, R={r_enc} | PWM: L={l_curr:.1f}, R={r_curr:.1f}")
                     
        finally:
            self.stop()

    def _interpolate_pwm(self, target_tps, side):
        """Finds the PWM value for a target TPS using linear interpolation."""
        side_idx = 0 if side == 'l' else 1
        
        # Create list of (TPS, PWM) points for the specific motor
        points = sorted([(tps[side_idx], pwm) for pwm, tps in self.calibration_points.items()])
        
        # Clamp to bounds
        if target_tps <= points[0][0]:
            return points[0][1]
        if target_tps >= points[-1][0]:
            return points[-1][1]
            
        # Linear interpolation between points
        for i in range(len(points) - 1):
            tps1, pwm1 = points[i]
            tps2, pwm2 = points[i+1]
            if tps1 <= target_tps <= tps2:
                # Formula: y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
                return pwm1 + (target_tps - tps1) * (pwm2 - pwm1) / (tps2 - tps1)
        
        return 0.0
