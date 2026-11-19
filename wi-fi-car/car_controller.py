import json
import logging
import os
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class CarController:
    """
    Drives the car straight by keeping both wheels in sync on the encoders.

    The controller compares the *total* distance each wheel has travelled
    since the move started (not the speed over the last interval), so any
    lag - e.g. one wheel starting later because of stiction - is made up
    instead of turning into a permanent heading change.

    Encoders only see motor shaft rotation, not the ground. Wheels with
    different effective diameters (a bent/worn wheel) cover different
    distances for the same tick count, which no encoder logic can detect.
    That is what `trim` is for: it sets the tick ratio L/R that counts as
    "straight" and is tuned once from the UI, then saved to settings.json.
    """

    def __init__(self, driver, cfg):
        """cfg: the [drive] section of config.ini."""
        self.driver = driver
        self.settings_path = os.path.join(BASE_DIR, cfg.get('settings_file'))
        # Approximate maximum Ticks Per Second (at 100% PWM), from re-calibration after motor swap
        self.max_tps = 1107.17

        # Sync loop tuning (see config.ini for what each one does)
        self.sync_enabled = cfg.getboolean('sync')
        self.loop_interval = 1.0 / cfg.getfloat('loop_hz')
        self.kp = cfg.getfloat('kp')                        # PWM per tick of distance error
        self.ki = cfg.getfloat('ki')                        # PWM per tick*second of distance error
        self.max_correction = cfg.getfloat('max_correction')  # so the loop can never shut a wheel off
        self.min_pwm = cfg.getfloat('min_pwm')              # floor while moving
        self.stall_time = cfg.getfloat('stall_time')
        self.stall_grace = cfg.getfloat('stall_grace')
        self.diverge_time = cfg.getfloat('diverge_time')
        self.diverge_ticks = cfg.getfloat('diverge_ticks')

        # Trim: % difference in wheel travel needed to go straight.
        # > 0 makes the left wheel turn more (steers right), < 0 steers left.
        self.max_trim = cfg.getfloat('max_trim')
        self.trim = 0.0
        self._load_settings()

        # Current motor state (read by the status logger / UI)
        self.current_l_pwm = 0.0
        self.current_r_pwm = 0.0
        self.distance_error = 0.0
        self.sync_state = 'idle'

        self._lock = threading.Lock()
        self._loop_thread = None
        self._loop_stop = threading.Event()

        # Calibration data points from re-calibration after motor swap: PWM -> (Left TPS, Right TPS)
        # Columns swapped vs SPEED.MD: it was recorded with the encoder pins crossed (Left = GPIO17).
        # PWM 1-13 omitted: dead zone where the motors don't overcome stiction (0 tps)
        self.calibration_points = {
            14: (262.99, 142.49),
            15: (290.49, 260.49),
            16: (318.99, 293.49),
            17: (352.49, 324.49),
            18: (379.48, 351.98),
            19: (405.98, 376.48),
            20: (430.98, 400.48),
            21: (452.98, 423.98),
            22: (476.98, 447.98),
            23: (500.98, 474.48),
            24: (522.48, 495.98),
            25: (543.48, 517.48),
            26: (562.98, 538.48),
            27: (585.48, 560.98),
            28: (601.47, 576.97),
            29: (620.47, 595.97),
            30: (637.97, 610.97),
            31: (654.47, 630.97),
            32: (669.97, 647.97),
            33: (685.47, 663.97),
            34: (699.47, 678.47),
            35: (710.97, 691.97),
            36: (726.47, 708.47),
            37: (740.47, 723.47),
            38: (752.47, 734.97),
            39: (763.97, 746.97),
            40: (775.97, 759.47),
            41: (786.47, 769.97),
            42: (796.97, 779.97),
            43: (807.97, 791.97),
            44: (817.97, 802.97),
            45: (827.47, 812.97),
            46: (834.96, 822.96),
            47: (844.96, 831.96),
            48: (853.92, 840.92),
            49: (859.96, 845.96),
            50: (868.46, 853.46),
            51: (875.46, 859.46),
            52: (883.96, 867.46),
            53: (890.46, 872.96),
            54: (893.46, 885.46),
            55: (901.46, 893.96),
            56: (909.96, 900.46),
            57: (917.96, 907.46),
            58: (923.46, 917.46),
            59: (927.46, 916.46),
            60: (932.96, 916.96),
            61: (937.96, 927.96),
            62: (942.45, 933.95),
            63: (947.96, 939.46),
            64: (952.46, 943.96),
            65: (956.46, 949.46),
            66: (959.96, 953.96),
            67: (964.46, 958.46),
            68: (968.46, 962.96),
            69: (972.46, 967.46),
            70: (974.46, 971.46),
            71: (978.93, 976.43),
            72: (983.95, 980.45),
            73: (987.46, 983.96),
            74: (991.46, 988.46),
            75: (994.96, 990.96),
            76: (996.94, 994.44),
            77: (999.96, 999.46),
            78: (1002.95, 999.95),
            79: (1006.96, 1005.46),
            80: (1009.96, 1006.46),
            81: (1011.46, 1007.96),
            82: (1014.46, 1010.46),
            83: (1016.96, 1012.96),
            84: (1020.96, 1015.96),
            85: (1023.96, 1018.96),
            86: (1027.46, 1020.96),
            87: (1030.45, 1024.45),
            88: (1033.46, 1028.46),
            89: (1036.96, 1031.96),
            90: (1040.46, 1036.46),
            91: (1044.45, 1040.45),
            92: (1048.46, 1044.96),
            93: (1045.96, 1043.96),
            94: (1051.96, 1052.96),
            95: (1056.95, 1059.95),
            96: (1062.96, 1066.95),
            97: (1069.95, 1074.45),
            98: (1072.95, 1076.95),
            99: (1073.95, 1077.95),
            100: (1104.92, 1109.42)
        }

        # (TPS, PWM) curves per motor, sorted by TPS for interpolation
        self._l_curve = sorted((tps[0], pwm) for pwm, tps in self.calibration_points.items())
        self._r_curve = sorted((tps[1], pwm) for pwm, tps in self.calibration_points.items())

    # ---------------------------------------------------------------- public API

    def drive(self, speed_pct, direction='f'):
        """Drives straight. direction: 'f' forward, 'b' backward."""
        sign = -1 if direction == 'b' else 1
        logging.info(f"Driving {direction} at {speed_pct}% (trim {self.trim:+.1f}%)")
        self._move(speed_pct, sign, sign)

    def turn(self, speed_pct, side):
        """Turns in place. side: 'l' left, 'r' right. Wheels are synced too, so it pivots on the spot."""
        logging.info(f"Turning {'Left' if side == 'l' else 'Right'} at {speed_pct}%")
        if side == 'l':
            self._move(speed_pct, -1, 1)
        else:
            self._move(speed_pct, 1, -1)

    def stop(self):
        """Stops the car."""
        with self._lock:
            self._stop_loop()
            self._halt()

    def drive_stabilized(self, speed_pct, duration, direction='f'):
        """Drives straight for a fixed duration, then stops."""
        self.drive(speed_pct, direction)
        time.sleep(duration)
        self.stop()

    def set_trim(self, trim):
        """Sets and saves the trim (%). Applies immediately, also while driving."""
        self.trim = max(-self.max_trim, min(self.max_trim, float(trim)))
        self._save_settings()
        logging.info(f"Trim set to {self.trim:+.1f}%")
        return self.trim

    def get_pwms_for_speed(self, speed_pct):
        """Feed-forward PWM (Left, Right) for a speed %, including trim, from calibration data."""
        if speed_pct <= 0:
            return 0.0, 0.0
        kl, kr = self._trim_factors()
        target_tps = (speed_pct / 100.0) * self.max_tps
        l_pwm = max(self.min_pwm, self._interpolate_pwm(target_tps * kl, self._l_curve))
        r_pwm = max(self.min_pwm, self._interpolate_pwm(target_tps * kr, self._r_curve))
        return round(l_pwm, 1), round(r_pwm, 1)

    def get_status(self):
        l_enc, r_enc = self.driver.get_encoders()
        return {
            'l_ticks': l_enc,
            'r_ticks': r_enc,
            'l_pwm': self.current_l_pwm,
            'r_pwm': self.current_r_pwm,
            'error': round(self.distance_error, 1),
            'trim': self.trim,
            'sync': self.sync_state,
        }

    # ---------------------------------------------------------------- internals

    def _move(self, speed_pct, l_sign, r_sign):
        with self._lock:
            self._stop_loop()
            if speed_pct <= 0:
                self._halt()
                return
            self.driver.reset_encoders()
            self._loop_stop.clear()
            self._loop_thread = threading.Thread(
                target=self._control_loop, args=(speed_pct, l_sign, r_sign), daemon=True
            )
            self._loop_thread.start()

    def _stop_loop(self):
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_stop.set()
            self._loop_thread.join()
        self._loop_thread = None

    def _halt(self):
        self.current_l_pwm = 0.0
        self.current_r_pwm = 0.0
        self.distance_error = 0.0
        self.sync_state = 'idle'
        self.driver.stop()

    def _trim_factors(self):
        k = self.trim / 200.0
        return 1.0 + k, 1.0 - k

    def _control_loop(self, speed_pct, l_sign, r_sign):
        """
        PI controller on the accumulated, trim-normalised distance difference.
        Correction is applied symmetrically (ahead wheel down, behind wheel up)
        and is bounded, and each wheel stays >= min_pwm, so a wheel is never
        driven to a stop by the controller. If one wheel stops producing ticks
        (bad contact, dead encoder) the loop falls back to plain feed-forward
        instead of chasing a sensor that will never catch up.
        """
        l_dist = r_dist = 0.0     # trim-normalised ticks since start
        integral = 0.0
        err = 0.0
        l_idle = r_idle = 0.0     # how long each wheel has produced no ticks
        fault = None
        diverged = False
        sat_since = sat_err = None  # when correction hit its limit, and |err| at that moment
        l_prev, r_prev = self.driver.get_encoders()
        start = last = time.monotonic()
        self.sync_state = 'ok' if self.sync_enabled else 'off'

        while True:
            now = time.monotonic()
            dt = now - last
            last = now

            l_enc, r_enc = self.driver.get_encoders()
            dl, dr = l_enc - l_prev, r_enc - r_prev
            l_prev, r_prev = l_enc, r_enc

            l_idle = 0.0 if dl else l_idle + dt
            r_idle = 0.0 if dr else r_idle + dt
            l_stalled, r_stalled = l_idle >= self.stall_time, r_idle >= self.stall_time
            stalled = None
            if now - start >= self.stall_grace and l_stalled != r_stalled:
                stalled = 'left' if l_stalled else 'right'

            # Normalise ticks by trim, incrementally, so a trim change mid-drive
            # only affects future ticks and doesn't cause a jump.
            kl, kr = self._trim_factors()

            if diverged or not self.sync_enabled:
                correction = 0.0
            elif stalled:
                sat_since = None
                if fault != stalled:
                    logging.warning(f"Sync: no ticks from {stalled} wheel for {self.stall_time}s "
                                    f"(bad contact / encoder?) - driving without sync")
                    fault = stalled
                    self.sync_state = f'fault: {stalled}'
                integral = err = correction = 0.0
            else:
                if fault:
                    logging.info(f"Sync: {fault} wheel is back, resuming sync")
                    fault = None
                    self.sync_state = 'ok'
                    l_dist = r_dist = 0.0  # don't try to make up distance lost during the fault
                else:
                    l_dist += dl / kl
                    r_dist += dr / kr
                err = l_dist - r_dist          # > 0: left is ahead
                integral += err * dt
                i_limit = (self.max_correction / 2) / self.ki
                integral = max(-i_limit, min(i_limit, integral))
                correction = self.kp * err + self.ki * integral
                correction = max(-self.max_correction, min(self.max_correction, correction))

                # Correction maxed out and the gap still grows: the loop makes it worse,
                # e.g. encoders wired to the opposite motors. Drive without sync.
                if abs(correction) < self.max_correction:
                    sat_since = None
                elif sat_since is None:
                    sat_since, sat_err = now, abs(err)
                elif now - sat_since >= self.diverge_time and abs(err) - sat_err > self.diverge_ticks:
                    logging.warning(f"Sync: error keeps growing at max correction (err={err:.0f}) - "
                                    f"encoders crossed / wheel blocked? Driving without sync")
                    diverged = True
                    self.sync_state = 'fault: diverging'
                    integral = correction = 0.0

            l_ff, r_ff = self.get_pwms_for_speed(speed_pct)
            l_pwm = l_ff - correction
            r_pwm = r_ff + correction
            # Keep within 100 while preserving the difference between wheels
            over = max(l_pwm, r_pwm) - 100.0
            if over > 0:
                l_pwm -= over
                r_pwm -= over
            l_pwm = max(self.min_pwm, min(100.0, l_pwm))
            r_pwm = max(self.min_pwm, min(100.0, r_pwm))

            self.distance_error = err
            self.current_l_pwm = round(l_pwm * l_sign, 1)
            self.current_r_pwm = round(r_pwm * r_sign, 1)
            self.driver.set_pwm(self.current_l_pwm, self.current_r_pwm)

            if self._loop_stop.wait(self.loop_interval):
                break

    @staticmethod
    def _interpolate_pwm(target_tps, curve):
        """Finds the PWM value for a target TPS on a (TPS, PWM) curve using linear interpolation."""
        if target_tps <= curve[0][0]:
            return curve[0][1]
        if target_tps >= curve[-1][0]:
            return curve[-1][1]
        for (tps1, pwm1), (tps2, pwm2) in zip(curve, curve[1:]):
            if tps1 <= target_tps <= tps2:
                if tps2 == tps1:
                    return pwm1
                return pwm1 + (target_tps - tps1) * (pwm2 - pwm1) / (tps2 - tps1)
        return curve[-1][1]

    # ---------------------------------------------------------------- settings

    def _load_settings(self):
        try:
            with open(self.settings_path) as f:
                data = json.load(f)
            self.trim = max(-self.max_trim, min(self.max_trim, float(data.get('trim', 0.0))))
            logging.info(f"Loaded settings: trim {self.trim:+.1f}%")
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as e:
            logging.warning(f"Could not read {self.settings_path}: {e}")

    def _save_settings(self):
        try:
            tmp = self.settings_path + '.tmp'
            with open(tmp, 'w') as f:
                json.dump({'trim': self.trim}, f)
            os.replace(tmp, self.settings_path)
        except OSError as e:
            logging.error(f"Could not save {self.settings_path}: {e}")
