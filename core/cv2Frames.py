import cv2
import base64

class cv2_backend:
    def __init__(self, camera:str="0", backend:str="dshow", resolution:str="1270x720", quality:int=80) -> None:

        try:
            camera = int(camera)
        except:
            pass

        if backend == "dshow":
            video_capture = cv2.VideoCapture((camera), cv2.CAP_DSHOW)
        elif backend == "ffmpeg":
            video_capture = cv2.VideoCapture((camera), cv2.CAP_FFMPEG)
        elif backend == "gstreamer":
            video_capture = cv2.VideoCapture((camera), cv2.CAP_GSTREAMER)
        elif backend == "v4l":
            video_capture = cv2.VideoCapture((camera), cv2.CAP_V4L2)
        elif backend == "auto":
            video_capture = cv2.VideoCapture((camera))

        width, height = resolution.split('x')
        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))

        self.success = video_capture.isOpened()
        self.cap = video_capture
        self.quality = quality

    def frame(self):
        """
        generate a single, base64 encoded frame in .webp
        """

        success, frame = self.cap.read()

        if not success:
            return False
        
        _, buffer = cv2.imencode('.webp', frame, [cv2.IMWRITE_WEBP_QUALITY, int(self.quality)])

        #frame_encoded = base64.b64encode(buffer.tobytes()).decode('utf-8')
        frame_encoded = base64.b64encode(buffer).decode('utf-8')

        return frame_encoded