
import numpy as np


class Rotation(object):

    def __init__(self, lat, lon, rotation_angle):
        self.lat = lat
        self.lon = lon
        self.rotation_angle = rotation_angle

    @property
    def origin(self):
        return [self.lat, self.lon]

    #Argus to local
    def local_to_argus(self, coords):
        coords = self._rotate(coords) - self.origin
        return coords

    def argus_to_local(self, coords):
        coords = self._rotate(coords, positive=False) + self.origin
        return coords

    def _rotate(self, coords, positive=True):
        if not positive:
            theta = np.deg2rad(-self.rotation_angle)
        else:
            theta = np.deg2rad(self.rotation_angle)

        rotation_matrix = np.array([
            [np.cos(theta), np.sin(theta)],
            [-np.sin(theta), np.cos(theta)]
         ])

        rotated_coords = np.dot(rotation_matrix, coords.T)
        return rotated_coords.T
