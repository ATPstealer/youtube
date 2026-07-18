import cv2
import logging
import numpy as np
import time
import subprocess

class CameraDriver:
    def __init__(self):
        self.mock_mode = False
        self.video = None
        self.proc = None # Subprocess for rpicam-vid fallback
        
        # Pipelines optimized for Raspberry Pi Camera Module 3 (IMX708)
        # We prioritize native resolutions and common stable formats.
        pipelines = [
            (
                "libcamerasrc ! "
                "video/x-raw,width=1536,height=864,framerate=30/1 ! "
                "videoconvert ! "
                "videoscale ! "
                "video/x-raw,format=BGR,width=640,height=360,framerate=30/1 ! "
                "appsink drop=true max-buffers=1 sync=false",
                "GStreamer libcamerasrc"
            )
        ]

        for pipeline_str, name in pipelines:
            try:
                logging.info(f"Trying camera initialization: {name}")
                if pipeline_str is None:
                    # Try CAP_V4L2 then default
                    self.video = cv2.VideoCapture(0, cv2.CAP_V4L2)
                    if not self.video.isOpened():
                        self.video = cv2.VideoCapture(0)
                else:
                    self.video = cv2.VideoCapture(pipeline_str, cv2.CAP_GSTREAMER)
                
                if self.video.isOpened():
                    # Wait for first frame (GStreamer needs time to start)
                    success = False
                    start_time = time.time()
                    while time.time() - start_time < 3.0: # 3 seconds timeout
                        ret, _ = self.video.read()
                        if ret:
                            success = True
                            break
                        time.sleep(0.1)
                    
                    if success:
                        logging.info(f"Camera initialized successfully using {name}")
                        return
                    else:
                        logging.warning(f"Opened {name} but could not read frames.")
                        self.video.release()
                        self.video = None
                else:
                    logging.debug(f"Could not open {name}")
            except Exception as e:
                logging.warning(f"Error during {name} initialization: {e}")

        # Final physical camera attempt: subprocess rpicam-vid
        if self._init_subprocess():
            return

        logging.error("All camera initialization methods failed. Switching to Mock Mode.")
        self.mock_mode = True

    def _init_subprocess(self):
        """Fallback to rpicam-vid MJPEG stream if GStreamer fails."""
        try:
            logging.info("Trying camera initialization: rpicam-vid subprocess fallback")
            cmd = [
                'rpicam-vid', '-t', '0', '--inline', '--codec', 'mjpeg',
                '--width', '640', '--height', '360', '--framerate', '30',
                '--nopreview', '-o', '-'
            ]
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
            
            # Check if we can get at least one frame
            time.sleep(1.0)
            frame = self._get_frame_from_subprocess()
            if frame:
                logging.info("Camera initialized successfully using rpicam-vid subprocess")
                return True
            else:
                logging.warning("rpicam-vid subprocess failed to provide frames.")
                self.proc.terminate()
                self.proc = None
                return False
        except Exception as e:
            logging.error(f"rpicam-vid fallback error: {e}")
            return False

    def _get_frame_from_subprocess(self):
        """Reads one MJPEG frame from subprocess stdout."""
        if not self.proc or self.proc.poll() is not None:
            return None
        
        try:
            # Search for JPEG Start Of Image (SOI)
            while True:
                byte = self.proc.stdout.read(1)
                if not byte: return None
                if byte == b'\xff':
                    byte = self.proc.stdout.read(1)
                    if byte == b'\xd8':
                        break
            
            # Read until JPEG End Of Image (EOI)
            frame_data = b'\xff\xd8'
            while True:
                chunk = self.proc.stdout.read(4096)
                if not chunk: break
                frame_data += chunk
                eoi_idx = frame_data.find(b'\xff\xd9')
                if eoi_idx != -1:
                    return frame_data[:eoi_idx+2]
        except Exception as e:
            logging.error(f"Error reading frame from subprocess: {e}")
            return None

    def __del__(self):
        if hasattr(self, 'video') and self.video and self.video.isOpened():
            self.video.release()
        if hasattr(self, 'proc') and self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except:
                pass

    def _get_mock_frame(self):
        """Генерирует тестовый кадр, если реальная камера недоступна."""
        # Создаем темно-серое изображение
        height, width = 480, 640
        image = np.zeros((height, width, 3), np.uint8)
        image[:] = (50, 50, 50)
        
        # Добавляем текст
        text = "MOCK CAMERA"
        timestamp = time.strftime("%H:%M:%S")
        cv2.putText(image, text, (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        cv2.putText(image, "NO PHYSICAL CAMERA DETECTED", (130, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(image, timestamp, (260, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

    def get_frame(self):
        """Захватывает кадр и возвращает его в формате JPEG bytes."""
        if self.mock_mode:
            return self._get_mock_frame()
            
        if self.proc:
            frame = self._get_frame_from_subprocess()
            if frame:
                return frame
            else:
                logging.error("Failed to capture frame from subprocess. Returning mock frame.")
                return self._get_mock_frame()

        success, image = self.video.read()
        if not success:
            logging.error("Failed to capture frame from camera. Returning mock frame.")
            return self._get_mock_frame()
        
        # Опционально: обработка изображения
        # image = cv2.resize(image, (640, 480))
        
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
