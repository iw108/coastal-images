# -*- coding: utf-8 -*-
"""
Created on Mon Apr 30 13:51:09 2018

@author: isaacwilliams
"""


import numpy as np
from scipy.interpolate import griddata

from .utils import open_with_retries, parse_datetime, timestamp_to_datetime


GPS_FILE = ('http://opendap.tudelft.nl/thredds/dodsC/data2/zandmotor/'
            'morphology/JETSKI/surveypath/jetski_surveypath.nc')


LIDAR_FILE = ('http://opendap.deltares.nl/thredds/dodsC/'
              'opendap/rijkswaterstaat/kusthoogte/30dz1.nc')


class Lidar(object):

    file_path = LIDAR_FILE

    def __init__(self):
        self.timestamps = self.get_timestamps()

    def get_timestamps(self):

        with open_with_retries(self.file_path) as dataset:
            timestamps = dataset['time'][:] * (24 * 60 * 60)

        timestamps = [timestamp_to_datetime(timestamp) for timestamp in timestamps]
        return np.asarray(timestamps)


    def get_timestamp_index(self, datetime_obj):
        datetime_obj = parse_datetime(datetime_obj)
        return abs(self.timestamps - datetime_obj).argmin()


    def is_valid_timestamp_index(self, index):

        if not isinstance(index, int):
            raise TypeError('Index must be integer')

        if isinstance(index, int) and ((index < 0) or index > len(self.timestamps)):
            raise ValueError('Enter a valid integer')


    def load_topo_from_datetime(self, datetime_obj):

        index = self.get_timestamp_index(datetime_obj)
        lon, lat, elev = self.load_topo_from_index(index)

        topo_timestamp = self.timestamps[index]
        return lon, lat, elev, topo_timestamp


    def load_topo_from_index(self, index):

        self.is_valid_timestamp_index(index)

        with open_with_retries(self.file_path) as dataset:
            lon = dataset['x'][:]
            lat = dataset['y'][:]
            elev = dataset['z'][index]
        return lon, lat, elev


    @classmethod
    def get_topo(cls, datetime_obj):
       return cls().load_topo_from_datetime(datetime_obj)


class GPS(Lidar):

    file_path = GPS_FILE

    def load_topo_from_index(self, index):
        with open_with_retries(self.file_path) as dataset:
            xyz = dataset['survey_path_RD'][index]
            lon, lat, elev = xyz[xyz.mask[:, 0] == False, :].data.T
        return lon, lat, elev


    @staticmethod
    def interpolate_data(lon, lat, elev, lon_lims=(7e4, 7.5e4), lat_lims=(4.5e5, 4.55e5),
                         lon_spacing=2, lat_spacing=2):

        lon_array = np.arange(*lon_lims, lon_spacing)
        lat_array = np.arange(*lat_lims, lat_spacing)

        xx, yy  = np.meshgrid(lon_array, lat_array)
        interpolated_elev = griddata((lon, lat), elev, (xx, yy))

        return lon_array, lat_array, interpolated_elev
