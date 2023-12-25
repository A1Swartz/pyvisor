import cv2
import io
import time
import threading
from vidgear.gears import CamGear
import core.coolPrint as log
import logging

import numba as nb
import numpy as np

@nb.jit(forceobj=True)
def convertGrayscale(image1, image2):
    # Optimized grayscale conversion
    gimage1 = cv2.merge([image1[:, :, 0]])  # Direct memory access
    gimage2 = cv2.merge([image2[:, :, 0]])

    return [gimage1, gimage2]

@nb.jit(forceobj=True)
def _detect_changes(sub_image, previous_sub_image):
    """
    Detects changes between two sub-images.
    Args:
        sub_image: The current sub-image.
        previous_sub_image: The previous sub-image.
    Returns:
        True if changes were detected, False otherwise.
    """

    # Optimized grayscale conversion
    grayscale_sub_image, grayscale_previous_sub_image = convertGrayscale(sub_image, previous_sub_image)

    # Optimized difference calculation using NumPy
    difference_image = np.abs(grayscale_sub_image.astype(np.int32) - grayscale_previous_sub_image.astype(np.int32))

    # Combined thresholding and counting
    non_zero_pixels = np.count_nonzero(difference_image > 10)

    return non_zero_pixels >= 1

class cv2_backend:

        
    def __init__(self,
                 config=None,
                camera:str="0", 
                backend:str="dshow", 
                resolution:str="1280x720", 
                framerate:int=60,
                debug:bool=False,
                cv2ng:bool=True) -> None:
        

        if config is not None:
            backend = config["cvBackend"]["value"]
            resolution = config["resolution"]["value"]
            camera = config["camera"]["value"]
            framerate = config["framerate"]["value"]
            cv2ng = config["cv2-ng"]["value"]

        self._useGear = cv2ng

        try:
            camera = int(camera)
        except:
            pass

        chosenBackend = None

        if backend == "dshow":
            chosenBackend = cv2.CAP_DSHOW
        elif backend == "ffmpeg":
            chosenBackend = cv2.CAP_FFMPEG
        elif backend == "gstreamer":
            chosenBackend = cv2.CAP_GSTREAMER
        elif backend == "v4l":
            chosenBackend = cv2.CAP_V4L2
        elif backend == 'mjpeg':
            chosenBackend = cv2.CAP_OPENCV_MJPEG
        elif backend == 'mfx':
            chosenBackend = cv2.CAP_INTEL_MFX
        elif backend == "msmf":
            log.warn("MSMF backend detected as the chosen backend - this WILL take upwards of 30 seconds to 5 minutes")
            chosenBackend = cv2.CAP_MSMF
        elif backend == "auto":
            log.warn("auto backend detected as the chosen backend - this might take upwards of a minute")
            chosenBackend = cv2.CAP_ANY

            if self._useGear:
                chosenBackend = 0

        if not self._useGear:


            video_capture = cv2.VideoCapture((camera), chosenBackend)


            width, height = resolution.split('x')
            video_capture.set(cv2.CAP_PROP_CONVERT_RGB, 0)
            video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            video_capture.set(cv2.CAP_PROP_FPS, int(framerate))
            video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

            video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
            video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))


            self.success = video_capture.isOpened()
            self.cap = video_capture
        else:
            width, height = resolution.split('x')

            options = {
                "CAP_PROP_FPS": int(framerate),
                "CAP_PROP_FRAME_WIDTH": int(width),
                "CAP_PROP_FRAME_HEIGHT": int(height),
                "CAP_PROP_FOURCC": cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
            }

            logging.getLogger("vidgear.gears").setLevel(logging.ERROR)
            self.cap = CamGear(source=camera, logging=False, backend=chosenBackend, **options).start()
            self.success = True

        self.frame = None
        self.fps = 0

        self._framesSent = 0
        self._debug = debug

        threading.Thread(target=self.frameRate, daemon=True).start()

    def grabFrame(self, encode=False):

        frm = self.frame # set our frame value

        #self.frame = None 
        # set it to none, becuase;
        # if we try to encode a frame while opencv is still grabbing the frame, it'll *skip back* and spike
        # it also will introduce a LOT of latency, but doing this makes the client skip over the frame
        # and not show it, so it just tries to grab a frame again, where it SHOULD be successful
        # if not, just do the same thing again
        
        # 1 day after, i was wondering why the client framerate was so low
        # above was the reason why

        if frm is None:
            return False

        if not encode:
            return frm
        else:
            return self.encode(frm)
        
    def encode(self, frame):
        return cv2.imencode(".jpeg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])[-1].tobytes()
        
    def split_image(self, image, split=4):
        """
        Splits an image into 16 equal sub-images.
        Args:
            image: The image to split.
        Returns:
            A list of 16 sub-images.
        """

        height, width = image.shape[:2]
        sub_height = height // split
        sub_width = width // split
        sub_images = []
        for y in range(split):
            for x in range(split):
                sub_image = image[y * sub_height:(y + 1) * sub_height, x * sub_width:(x + 1) * sub_width]
                sub_images.append(sub_image)

        return sub_images
    
    def detect_changes(self, sub_image, previous_sub_image):
        """
        Detects changes between two sub-images.
        Args:
            sub_image: The current sub-image.
            previous_sub_image: The previous sub-image.
        Returns:
            True if changes were detected, False otherwise.
        """

        # Optimized grayscale conversion
        grayscale_sub_image = cv2.merge([sub_image[:, :, 0]])  # Direct memory access
        grayscale_previous_sub_image = cv2.merge([previous_sub_image[:, :, 0]])

        # Optimized difference calculation using NumPy
        difference_image = np.abs(grayscale_sub_image.astype(np.int32) - grayscale_previous_sub_image.astype(np.int32))

        # Combined thresholding and counting
        non_zero_pixels = np.count_nonzero(difference_image > 10)

        return non_zero_pixels >= 1
    
    def setFrame(self):
        """
        generate a single frame in .webp
        """
        
        success, frame = self.cap.read()

        if not success:
            return False
        
        _, buffer = cv2.imencode('.jpeg', frame)

        self.frame = io.BytesIO(buffer)

    def autoFrames(self):
        a = threading.Thread(target=self._SetFrames, daemon=True)
        a.start()

        return a

    def _SetFrames(self, noEncode=True):
        while True:


            if not self._useGear:
                success, frame = self.cap.read()
            else:
                frame = self.cap.read()
                success = True if frame is not None else False

            if not success or frame is None:
                print("[OpenCV] error grabbing frame from camera")
                continue
            
            if not noEncode: # encode it:
                _, buffer = cv2.imencode('.jpeg', frame)

                self.frame = buffer.tobytes()
            else:
                self.frame = frame

            self._framesSent += 1

    def frameRate(self):
        """
        calculate framerate
        """

        if self._debug:
            threading.Thread(target=self.frameRateHelper, daemon=True).start()


        if not self._useGear:
            self.fps = 0

            oldTime = round((time.time() % 60))
            oldFramesSent = 0
            while True:
                if self._framesSent != oldFramesSent:
                    curTime = round((time.time() % 60))

                    if oldTime != curTime:
                        try:
                            self.fps = round((self._framesSent - oldFramesSent) / (oldTime / curTime), 4)
                        except ZeroDivisionError:
                            pass

                        oldTime = round((time.time() % 60))
                        oldFramesSent = self._framesSent

                time.sleep(0.001)
        else:
            self.fps = self.cap.framerate
            time.sleep(0.075)

    def frameRateHelper(self):
        """
        print framerate every 500ms
        """

        while True:
            print(self.fps)
            time.sleep(0.5)
