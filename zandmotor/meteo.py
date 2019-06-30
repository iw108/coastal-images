
from calendar import timegm

import numpy as np
from pandas import DataFrame

from .utils import parse_datetime, timestamp_to_datetime, open_with_retries


METEO_FILE = ("https://zandmotordata.nl/thredds/dodsC/"
              "zandmotor/meteohydro/meteo/meteo.nc")


METEO_VARIABLES = [
    'AirTemp_Avg',
    'RelHumid_Avg',
    'AirTemp_Avg',
    'SolarRad_Avg',
    'Rainfall_Tot',
    'WindSpeed_Avg',
    'Barometer_Avg',
    'WindDir_Avg',
    'WindSpeed_Min',
    'WindSpeed_Max',
    'WindDir_Std'
]


def average_angles(angles, radians=False):

    if not radians:
        angles = np.deg2rad(angles)

    # decompose angles into components and average
    east = np.sin(angles).mean()
    west = np.cos(angles).mean()

    # recompose to angles
    theta = np.arctan2(east, west) % (2*np.pi)

    if not radians:
        return np.rad2deg(theta)
    return theta


def parse_variables(variables):

    if not isinstance(variables, (tuple, list)):
        raise TypeError

    if not all(variable in METEO_VARIABLES for variable in variables):
        raise ValueError

    return variables


def get_meteo(time_start, time_end, variables):

    start, end = map(lambda t: parse_datetime(t), (time_start, time_end))
    parse_variables(variables)

    # Open file and extract
    with open_with_retries(METEO_FILE, retries=3) as dataset:
        timestamps = dataset['time'][:]

        mask = ((timestamps <= timegm(end.timetuple())) &
                (timestamps >= timegm(start.timetuple())))

        data = {var: dataset.variables[var][mask] for var in variables}

    dataframe = DataFrame(data).set_index(timestamps[mask])
    dataframe.index = dataframe.index.map(lambda ts: timestamp_to_datetime(ts))

    return dataframe
