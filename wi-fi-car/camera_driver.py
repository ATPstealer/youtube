import cv2
import logging

class CameraDriver:
    def __init__(self):
        self.video = cv2.VideoCapture(0)
        if not self.video.isOpened():
            logging.error("Could not open video device")
        else:
            logging.info("Camera initialized successfully")

    def __del__(self):
        if self.video.isOpened():
            self.video.release()

    def get_frame(self):
        """Captures a frame and returns it as JPEG bytes."""
        success, image = self.video.read()
        if not success:
            return None
        
        # You can add image processing here (resize, flip, etc.)
        # image = cv2.flip(image, 0) # Flip if camera is upside down
        
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
