
import cv2
import numpy as np


class Camera(object):

    def __init__(self, camera_matrix, dist_coefs, frame_size, **kwargs):

        self.camera_matrix = camera_matrix
        self.dist_coefs = dist_coefs
        self.frame_size = frame_size

        self.opt_camera_matrix = cv2.getOptimalNewCameraMatrix(
            camera_matrix, dist_coefs, frame_size, 0, frame_size
        )[0]

        self.rotation_matrix = kwargs.get('rotation_matrix', None)
        self.translation_vector = kwargs.get('translation_vector', None)

    @property
    def focal_lengths(self):
        return np.array([
            self.opt_camera_matrix[0, 0], self.opt_camera_matrix[1, 1]
        ])

    @property
    def principal_point(self):
        return np.array([
            self.opt_camera_matrix[0, 2], self.opt_camera_matrix[1, 2]
        ])

    @property
    def field_of_view(self):
        field_of_view = 2 * np.arctan(
            self.frame_size[0]/(2 * self.opt_camera_matrix[0, 0])
        )
        return field_of_view

    @property
    def is_rectified(self):

        if (isinstance(self.rotation_matrix, np.ndarray)
                and isinstance(self.translation_vector, np.ndarray)):
            return True
        return False


    def undistort_points(self, points):
        undistorted_points = cv2.undistortPoints(
            points.reshape(-1, 1, 2), self.opt_camera_matrix, self.dist_coefs,
            P=self.opt_camera_matrix
        )
        return undistorted_points.reshape(points.shape)

    def undistort_image(self, image):
        return cv2.undistort(
            image, self.camera_matrix, self.dist_coefs, self.opt_camera_matrix
        )

    def rectify(self, object_points, image_points, distorted=False):

        if distorted:
            image_points = self.undistort_points(image_points)

        dist_coefs = np.zeros(4)

        rotation_vector, self.translation_vector = cv2.solvePnP(
            object_points, image_points, self.opt_camera_matrix, dist_coefs
        )[-2:]

        self.rotation_matrix = cv2.Rodrigues(rotation_vector)[0]


    def object_to_image_points(self, points):

        if not self.is_rectified:
            raise ValueError('Camera has to be rectified')

        object_points = points.reshape(-1, 1, 3)

        # object points in local camera coordinate system
        object_points_camera = (
            (self.rotation_matrix * object_points).sum(axis=2)
            + self.translation_vector.reshape(1, -1)
        )

        # calculate image coordinates
        scaled_object_points = (
            object_points_camera[:, :-1] / object_points_camera[:, -1].reshape(-1, 1)
        )

        image_points = (
            self.focal_lengths * scaled_object_points + self.principal_point
        )

        image_points = self._mask_image_points(image_points)
        return image_points


    def _mask_image_points(self, image_points):

        mask = (np.isnan(image_points) | (image_points < 0)
                    | (image_points >= np.array(self.frame_size)))

        return np.ma.masked_array(image_points, mask=mask)


    def projection_error(self, object_points, image_points):

        pixel_diff = (self.object_to_image_points(self, object_points).data
                          - image_points)

        return ((pixel_diff**2).sum(axis=1)**0.5).mean()
