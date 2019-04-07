# -*- coding: utf-8 -*-
"""
Created on Fri Apr 27 07:36:00 2018

@author: isaacwilliams
"""

import ephem
import numpy as np
import pyproj
import pytz


def parse_timezone(timezone_string):

    if not isinstance(timezone_string, str):
        raise TypeError('Timezone must be a string')

    if not timezone_string in pytz.all_timezones:
        raise ValueError(f'{timezone_string} not a valid timezone')

    return pytz.timezone(timezone_string)


class Solar(ephem.Observer):

    def __init__(self, lon, lat, elev=0, timezone='Europe/Amsterdam', in_degrees=True):

        self.in_degrees = in_degress
        self.lon, self.lat = np.deg2rad([lon, lat]) if in_degrees else (lon, lat)
        self.elev = elev
        self.tz =  parse_timezone(tz)


    @property
    def coords(coords):
        if self.in_dregrees:
            return np.rad2deg([self.lon, self.lat])
        return self.lon, self.lat


    def sun_position(self, date):

        self.date = self._process_input_date(date)
        position = ephem.Sun(self)
        position.compute(self)

        if self.in_degrees:
            return np.rad2deg([position.az, position.alt])
        return position.az, position.alt


    def daylight_hours(self, date):

        date = date.replace(hour = 0, minute = 0, second = 0)

        input_date = self._process_input_date(date)
        self.date = input_date

        sunrise = self.next_rising(ephem.Sun()).datetime()
        sunset = self.next_setting(ephem.Sun()).datetime()

        return self._process_output_date(sunrise), self._process_output_date(sunset)


    def _process_output_date(self, date):
        date = pytz.utc.localize(date)
        return date.astimezone(self.tz)


    def _process_input_date(self, date):

        if not date.tzinfo:
            date = self.tz.localize(date)

        return date.astimezone(pytz.utc)



def shad_pos(azimuth, altitude, height, offset = (0, 0), mode = 'rad'):

    if mode == 'deg':
        azimuth, altitude = list(map(lambda x: np.deg2rad(x), [azimuth, altitude]))

    angle = (azimuth + np.pi) % (2*np.pi)

    if altitude > 0:
        length = height/ np.tan(altitude)
    else:
        length = 0

    y0 = np.array([0, length])
    x0 = y0*0

    x1, y1 = rotate(angle, np.column_stack((x0, y0))).T

    return x1 + offset[0], y1 + offset[1]



def intersection (segment1, segment2):

    if not isinstance(segment1, np.ndarray) or segment1.shape != (2, 1, 2):
        raise ValueError('...')
    if not isinstance(segment2, np.ndarray) or segment2.shape != (2, 1, 2):
        raise ValueError('...')

    x1, y1, x2, y2  = segment1.flatten()
    x3, y3, x4, y4 = segment2.flatten()

    ua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
    ub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
    denominator = (y4 - y3)*(x2 - x1) - (x4 - x3)*(y2 - y1)


    if denominator != 0 and (ua != 0 and ub != 0):

        ua /= denominator
        ub /= denominator

        if (ua >= 0) and (ua <= 1) and (ub >= 0) and (ub <= 1):
            test  = True

        else:
            test = False

    else:

        if ((max([x1, x2]) < min([x3, x4])) | (max([x3, x4]) < min([x1, x2])) |
              (max([y1, y2]) < min([y3, y4])) |  (max([y3, y4]) < min([y1, y2]))):
            test = False

        else:
            test = True

    return test
