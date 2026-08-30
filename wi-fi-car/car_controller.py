import logging
import threading
import time

class CarController:
    def __init__(self, driver):
        self.driver = driver
        # Approximate maximum Ticks Per Second (at 100% PWM), from re-calibration after motor swap
        self.max_tps = 1107.17

        # Current motor state
        self.current_l_pwm = 0.0
        self.current_r_pwm = 0.0

        # Background thread that keeps the car driving straight during 'drive()'
        self._correction_thread = None
        self._correction_stop = threading.Event()

        # Straight-line correction tuning
        self._check_interval = 0.1    # 100ms
        self._diff_threshold = 5      # tick difference to trigger correction (1x decoding = 1/4 the ticks of before)
        self._correction_step = 1.0   # PWM units to decrease
        self._growth_step = 0.5       # PWM units to grow back

        # Calibration data points from re-calibration after motor swap: PWM -> (Left TPS, Right TPS)
        # PWM 1-13 omitted: dead zone where the motors don't overcome stiction (0 tps)
        self.calibration_points = {
            14: (142.49, 262.99),
            15: (260.49, 290.49),
            16: (293.49, 318.99),
            17: (324.49, 352.49),
            18: (351.98, 379.48),
            19: (376.48, 405.98),
            20: (400.48, 430.98),
            21: (423.98, 452.98),
            22: (447.98, 476.98),
            23: (474.48, 500.98),
            24: (495.98, 522.48),
            25: (517.48, 543.48),
            26: (538.48, 562.98),
            27: (560.98, 585.48),
            28: (576.97, 601.47),
            29: (595.97, 620.47),
            30: (610.97, 637.97),
            31: (630.97, 654.47),
            32: (647.97, 669.97),
            33: (663.97, 685.47),
            34: (678.47, 699.47),
            35: (691.97, 710.97),
            36: (708.47, 726.47),
            37: (723.47, 740.47),
            38: (734.97, 752.47),
            39: (746.97, 763.97),
            40: (759.47, 775.97),
            41: (769.97, 786.47),
            42: (779.97, 796.97),
            43: (791.97, 807.97),
            44: (802.97, 817.97),
            45: (812.97, 827.47),
            46: (822.96, 834.96),
            47: (831.96, 844.96),
            48: (840.92, 853.92),
            49: (845.96, 859.96),
            50: (853.46, 868.46),
            51: (859.46, 875.46),
            52: (867.46, 883.96),
            53: (872.96, 890.46),
            54: (885.46, 893.46),
            55: (893.96, 901.46),
            56: (900.46, 909.96),
            57: (907.46, 917.96),
            58: (917.46, 923.46),
            59: (916.46, 927.46),
            60: (916.96, 932.96),
            61: (927.96, 937.96),
            62: (933.95, 942.45),
            63: (939.46, 947.96),
            64: (943.96, 952.46),
            65: (949.46, 956.46),
            66: (953.96, 959.96),
            67: (958.46, 964.46),
            68: (962.96, 968.46),
            69: (967.46, 972.46),
            70: (971.46, 974.46),
            71: (976.43, 978.93),
            72: (980.45, 983.95),
            73: (983.96, 987.46),
            74: (988.46, 991.46),
            75: (990.96, 994.96),
            76: (994.44, 996.94),
            77: (999.46, 999.96),
            78: (999.95, 1002.95),
            79: (1005.46, 1006.96),
            80: (1006.46, 1009.96),
            81: (1007.96, 1011.46),
            82: (1010.46, 1014.46),
            83: (1012.96, 1016.96),
            84: (1015.96, 1020.96),
            85: (1018.96, 1023.96),
            86: (1020.96, 1027.46),
            87: (1024.45, 1030.45),
            88: (1028.46, 1033.46),
            89: (1031.96, 1036.96),
            90: (1036.46, 1040.46),
            91: (1040.45, 1044.45),
            92: (1044.96, 1048.46),
            93: (1043.96, 1045.96),
            94: (1052.96, 1051.96),
            95: (1059.95, 1056.95),
            96: (1066.95, 1062.96),
            97: (1074.45, 1069.95),
            98: (1076.95, 1072.95),
            99: (1077.95, 1073.95),
            100: (1109.42, 1104.92)
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
        Drives the car at a logical speed percentage, continuously correcting
        for one wheel running faster than the other using the encoders.
        direction: 'f' for forward, 'b' for backward.
        """
        self._stop_correction()

        l_base, r_base = self.get_pwms_for_speed(speed_pct)
        sign = -1 if direction == 'b' else 1

        self.current_l_pwm = l_base * sign
        self.current_r_pwm = r_base * sign
        logging.info(f"Driving {direction} at {speed_pct}% speed (L_PWM={self.current_l_pwm}, R_PWM={self.current_r_pwm})")

        self.driver.reset_encoders()
        self.driver.set_pwm(self.current_l_pwm, self.current_r_pwm)

        if speed_pct > 0:
            self._start_correction(l_base, r_base, sign)

    def turn(self, speed_pct, side):
        """
        Turns the car in place.
        side: 'l' for left, 'r' for right.
        """
        self._stop_correction()

        l_pwm, r_pwm = self.get_pwms_for_speed(speed_pct)
        if side == 'l':
            l_pwm_final, r_pwm_final = -l_pwm, r_pwm
            logging.info(f"Turning Left at {speed_pct}%")
        else:
            l_pwm_final, r_pwm_final = l_pwm, -r_pwm
            logging.info(f"Turning Right at {speed_pct}%")

        self.current_l_pwm = l_pwm_final
        self.current_r_pwm = r_pwm_final
        self.driver.set_pwm(l_pwm_final, r_pwm_final)

    def stop(self):
        """Stops the car."""
        self._stop_correction()
        self.current_l_pwm = 0.0
        self.current_r_pwm = 0.0
        self.driver.stop()

    def drive_stabilized(self, speed_pct, duration, direction='f'):
        """
        Drives the car straight for a fixed duration, then stops.
        """
        self.drive(speed_pct, direction)
        time.sleep(duration)
        self.stop()

    def _start_correction(self, l_base, r_base, sign):
        """Starts the background thread that keeps the car driving straight."""
        self._correction_stop.clear()
        self._correction_thread = threading.Thread(
            target=self._correction_loop, args=(l_base, r_base, sign), daemon=True
        )
        self._correction_thread.start()

    def _stop_correction(self):
        """Stops the background straight-line correction thread, if running."""
        if self._correction_thread and self._correction_thread.is_alive():
            self._correction_stop.set()
            self._correction_thread.join()
        self._correction_thread = None

    def _correction_loop(self, l_base, r_base, sign):
        """
        Runs until stopped, compensating for motor differences using encoders.
        If one wheel is running ahead (higher tick count), its PWM is reduced.
        Then it gradually grows back to the base value once levelled out.
        """
        l_curr, r_curr = l_base, r_base

        while not self._correction_stop.wait(self._check_interval):
            l_enc, r_enc = self.driver.get_encoders()
            diff = l_enc - r_enc

            if diff > self._diff_threshold:
                # Left is ahead, reduce its PWM
                l_curr -= self._correction_step
            elif diff < -self._diff_threshold:
                # Right is ahead, reduce its PWM
                r_curr -= self._correction_step
            else:
                # Within threshold, gradually return to base PWM
                if l_curr < l_base:
                    l_curr += self._growth_step
                if r_curr < r_base:
                    r_curr += self._growth_step

            # Clamp to [0, base]
            l_curr = max(0, min(l_curr, l_base))
            r_curr = max(0, min(r_curr, r_base))

            self.current_l_pwm = l_curr * sign
            self.current_r_pwm = r_curr * sign
            self.driver.set_pwm(l_curr * sign, r_curr * sign)

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
