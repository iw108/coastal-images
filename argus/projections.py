
import ephem
import numpy as np
import pyproj
from pytz import timezone as pytz_timezone, utc as pytz_utc, all_timezones


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


def parse_timezone(timezone_string):

    if not isinstance(timezone_string, str):
        raise TypeError('Timezone must be a string')

    if not timezone_string in all_timezones:
        raise ValueError(f'{timezone_string} not a valid timezone')

    return pytz_timezone(timezone_string)


class Solar(ephem.Observer):

    def __init__(self, lon, lat, elev=0, timezone='Europe/Amsterdam', in_degrees=True):

        self.in_degrees = in_degrees
        self.lon, self.lat = np.deg2rad([lon, lat]) if in_degrees else (lon, lat)
        self.elev = elev
        self.timezone =  parse_timezone(timezone)


    @property
    def coords(self):
        if self.in_degrees:
            return np.rad2deg([self.lon, self.lat])
        return self.lon, self.lat


    def sun_position(self, input_datetime):

        self.date = self._process_input_date(input_datetime)
        position = ephem.Sun(self)
        position.compute(self)

        if self.in_degrees:
            return np.rad2deg([position.az, position.alt])
        return position.az, position.alt


    def daylight_hours(self, input_datetime):

        input_datetime = input_datetime.replace(
            hour=0, minute=0, second=0
        )
        self.date = self.process_input_datetime(input_datetime)

        sunrise_datetime = self.process_output_datetime(
            self.next_rising(ephem.Sun()).datetime()
        )

        sunset_datetime = self.process_output_datetime(
            self.next_setting(ephem.Sun()).datetime()
        )

        return sunrise_datetime, sunset_datetime


    def process_output_datetime(self, datetime_obj):
        output_datetime = pytz_utc.localize(datetime_obj)
        return output_datetime.astimezone(self.timezone)


    def process_input_datetime(self, date):
        if not date.tzinfo:
            date = self.timezone.localize(date)
        return date.astimezone(pytz_utc)


def rotate(angle, points):

    rotation_matrix = np.array([
      [np.cos(angle), np.sin(angle)],
      [-np.sin(angle), np.cos(angle)]
    ])

    return np.dot(rotation_matrix, points.T).T


def shadow_position(azimuth, altitude, object_height, offset=(0, 0), in_degrees=False):

    if in_degrees:
        azimuth, altitude = np.deg2rad([azimuth, altitude])

    shadow_length = object_height/ np.tan(altitude)
    if altitude < 0:
        shadow_length = 0

    angle = (azimuth + np.pi) % (2 * np.pi)
    shadow_vector = np.array([[0, 0], [shadow_length, 0]])
    shadow_vector = (rotate(angle, shadow_vector).T
                     + np.asarray(offset).reshape(-1,1))

    return shadow_vector
