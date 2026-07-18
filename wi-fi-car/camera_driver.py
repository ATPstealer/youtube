import cv2
import logging
import numpy as np
import time

class CameraDriver:
    def __init__(self):
        self.mock_mode = False
        self.video = None
        
        # Pipelines optimized for Raspberry Pi Camera Module 3 (IMX708)
        # We prioritize native resolutions and common stable formats.
        pipelines = [
            # 1. 640x360 (Optimum for web streaming)
            (
                "libcamerasrc ! video/x-raw,width=1536,height=864,framerate=30/1 ! "
                "videoconvert ! videoscale ! video/x-raw,format=BGR,width=640,height=360 ! "
                "appsink drop=true max-buffers=1 sync=false",
                "GStreamer 640x360 (16:9)"
            ),
            # 2. 1280x720 (HD)
            (
                "libcamerasrc ! video/x-raw,width=1536,height=864,framerate=30/1 ! "
                "videoconvert ! videoscale ! video/x-raw,format=BGR,width=1280,height=720 ! "
                "appsink drop=true max-buffers=1 sync=false",
                "GStreamer 1280x720 (HD)"
            ),
            # 3. 1536x864 (Native Low-Res)
            (
                "libcamerasrc ! video/x-raw,width=1536,height=864,framerate=30/1 ! "
                "videoconvert ! video/x-raw,format=BGR ! "
                "appsink drop=true max-buffers=1 sync=false",
                "GStreamer 1536x864 (Native)"
            ),
            # 4. 2304x1296 (Native Mid-Res)
            (
                "libcamerasrc ! video/x-raw,width=2304,height=1296,framerate=30/1 ! "
                "videoconvert ! video/x-raw,format=BGR ! "
                "appsink drop=true max-buffers=1 sync=false",
                "GStreamer 2304x1296 (Native)"
            ),
            # 5. 4608x2592 (Native High-Res)
            (
                "libcamerasrc ! video/x-raw,width=4608,height=2592,framerate=14/1 ! "
                "videoconvert ! video/x-raw,format=BGR ! "
                "appsink drop=true max-buffers=1 sync=false",
                "GStreamer 4608x2592 (High-Res)"
            )
        ]

        for pipeline_str, name in pipelines:
            try:
                logging.info(f"Trying camera initialization: {name}")
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

        logging.error("All camera initialization methods failed. Switching to Mock Mode.")
        self.mock_mode = True

    def __del__(self):
        if hasattr(self, 'video') and self.video and self.video.isOpened():
            self.video.release()

    def _get_mock_frame(self):
        """Generates a test frame if the real camera is unavailable."""
        # Create a dark gray image
        height, width = 480, 640
        image = np.zeros((height, width, 3), np.uint8)
        image[:] = (50, 50, 50)
        
        # Add text
        text = "MOCK CAMERA"
        timestamp = time.strftime("%H:%M:%S")
        cv2.putText(image, text, (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        cv2.putText(image, "NO PHYSICAL CAMERA DETECTED", (130, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(image, timestamp, (260, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

    def get_frame(self):
        """Captures a frame and returns it in JPEG bytes format."""
        if self.mock_mode:
            return self._get_mock_frame()
            
        success, image = self.video.read()
        if not success:
            logging.error("Failed to capture frame from camera. Returning mock frame.")
            return self._get_mock_frame()
        
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
