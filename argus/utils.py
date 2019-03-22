
import cv2

class PerspectiveTransform(object):

    def __init__(self, initial_points, warped_points):
        self.initial_points = initial_points
        self.warped_points = warped_points

        self.homography = cv2.getPerspectiveTransform(
            object_points.astype('float32'), self.image_points.astype('float32')
        )

    def apply_perspective_transform(self, image):
        return cv2.warpPerspective(self.image, self.homography, self.image_points)

    @classmethod
    def perspective_transform(cls, points, warped_points, image):
        return cls(points, warped_points).apply_perspective_transform
