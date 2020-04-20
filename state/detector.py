import imageio
import imutils
import cv2 as cv
import numpy as np
from state.face import Face
from statistics import mean
from images.series import Image
from state.constant import CubletNames
from scipy.spatial import distance as dist


class FaceDetector:
    def __init__(self, cublet_margin=6):
        self.cublet_margin = cublet_margin

        self.cublet_colors = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "orange": (255, 165, 0),
            "white": (255, 255, 255),
        }

        self.template = imageio.imread("./outline-template.png")

    def detect_face(self, face_state: Face):
        """This function detects a face of the cube and finds the top left face corner and face size

        """

        greyscale_img = face_state.full_face_image.convert_to_greyscale()
        greyscale_img = cv.GaussianBlur(greyscale_img, (5, 5), 0)
        greyscale_img = cv.Canny(greyscale_img, 100, 200)
        greyscale_img = cv.dilate(greyscale_img, np.ones((5, 5)))

        best_fit_value = 0
        best_fit_loc = (None, None)
        best_fit_resize = None

        for scale in np.linspace(0.2, 1.0, 40)[::-1]:
            resized_img = imutils.resize(
                greyscale_img, width=int(greyscale_img.shape[1] * scale)
            )
            resized_percentage = greyscale_img.shape[1] / float(resized_img.shape[1])

            # Break if image is smaller than template
            if np.any(np.array(resized_img.shape) < np.array(self.template.shape)):
                break

            template_match = cv.matchTemplate(resized_img, self.template, cv.TM_CCOEFF)

            (_, maxVal, _, maxLoc) = cv.minMaxLoc(template_match)

            if maxVal * resized_percentage > best_fit_value:
                best_fit_value = maxVal * resized_percentage
                best_fit_loc = np.array(maxLoc)
                best_fit_resize = resized_percentage

        face_state.face_shape = (
            np.array(self.template.shape) * best_fit_resize
        ).astype(int)
        face_state.face_location = (best_fit_loc[::-1] * best_fit_resize).astype(int)

    def detect_cublets_shape(self, face_state: Face):
        """Split face into 9 seperate cubies
        
        """

        cublet_shape = ((face_state.face_shape - (6 * self.cublet_margin)) / 3).astype(
            "int"
        )

        for vert in range(3):
            for horiz in range(3):
                cublet_num = (vert * 3) + horiz

                cublet_location = (
                    face_state.face_location
                    + self.cublet_margin
                    + ((2 * self.cublet_margin + cublet_shape) * [vert, horiz])
                )

                face_state.set_cublet(
                    CubletNames.get_cublet_by_idx(cublet_num),
                    cublet_location,
                    cublet_shape,
                )

    def detect_cublets_color(self, face_state: Face):
        for cublet_name in CubletNames.get_cublet_order():
            cublet_pixels = face_state.get_cublet_image(cublet_name)
            mean_color = cublet_pixels.mean(axis=0).mean(axis=0)

            min_dist = np.inf
            cublet_color = None

            for rgb_name, rgb_value in self.cublet_colors.items():
                color_distance = dist.euclidean(rgb_value, mean_color)

                if color_distance < min_dist:
                    min_dist = color_distance
                    cublet_color = rgb_name

            face_state.cublets[cublet_name].color = cublet_color

        center_color = face_state[CubletNames.MC].color
        face_state.center_color = center_color