#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 10:47:14 2018

@author: williamsia
"""

from calendar import timegm
from datetime import datetime
import itertools
import requests

import numpy as np
import pandas as pd
import pytz


CATALOG = "http://argus-public.deltares.nl/catalog"
BASEPATH = "http://argus-public.deltares.nl/sites"

TIMEZONE = 'UTC'

SITE = 'zandmotor'
TIME_START = datetime(2013, 2, 20)
TIME_END = datetime(2018, 5, 16)

BASIC_IMAGE_TYPES = ['snap', 'timex', 'min', 'max', 'var']

CAMERA_NUMBERS = list(range(1, 13))


def timestamp_from_datetime(date_time):
    return timegm(date_time.timetuple())


def get_images(time_start, time_end, **kwargs):

    # parse the selected image types
    image_types = kwargs.get('image_types', [])
    if isinstance(image_types, str):
        image_types = [image_types]
    if not (isinstance(image_types, list) and
            all([image_type in BASIC_IMAGE_TYPES for image_type in image_types])):
        raise ValueError('image_types must be string or list of strings')

    # parse the selected cameras
    cameras = kwargs.get('cameras', [])

    if isinstance(cameras, int):
        cameras = [cameras]
    if not (isinstance(cameras, list) and
            all([camera in CAMERA_NUMBERS for camera in cameras])):
        raise ValueError('Camera must be integer or list of integers')


    # convert datetime to timestamps
    time_start = timestamp_from_datetime(time_start)
    time_end = timestamp_from_datetime(time_end)
    time_steps = np.linspace(
        time_start, time_end, max(2, int((time_end - time_start)/ (30 * 24 * 3600)))
    ).astype(int)

    parameters = {
        'site': 'zandmotor',
        'output':'json'
    }

    options = {
        'type': image_types,
        'camera': cameras
    }
    options = {key: value for key, value in options.items() if value}
    if options:
        keys = sorted(options.keys())
        combinations = list(itertools.product(*[options[key] for key in keys]))
        option_list = []
        for combination in combinations:
            option_list.append(
                {key: combination[index] for index, key in enumerate(keys)}
            )

    data = []
    for start_interval, end_interval in zip(time_steps[:-1], time_steps[1:]):
        parameters.update({
            'startEpoch': start_interval,
            'endEpoch': end_interval
        })
        if options:
            for item in option_list:
                parameters.update(item)
                data += requests.get(CATALOG, parameters).json()['data']
        else:
            data += requests.get(CATALOG, parameters).json()['data']

    # clean the output
    data = [item for item in data if item['type'] in BASIC_IMAGE_TYPES]
    return data


def images_to_pandas(data):

    df = pd.DataFrame(data).set_index('epoch')
    df.index = df.index.map(lambda timestamp: datetime.utcfromtimestamp(timestamp))


    indices = pd.date_range(
        start=df.index.min().floor('1H'), end=df.index.max().ceil('1H'),
        freq='30T', tz=pytz.utc
    )

    # Make multicolumn dataframe
    columns = [(camera, image) for camera
               in df.camera.unique() for image in df.type.unique()]

    df_images = pd.DataFrame(
        index=indices, columns=pd.MultiIndex.from_tuples(columns)
    )

    # Now fill data frame
    for index, row in df.iterrows():
        time_delta = (df_images.index - pytz.utc.localize(index))\
                     .abs().total_seconds()

        if delta.min() < 600:
           df_images.loc[df_images.index[time_delta.idxmin()], (row.camera, row.type)] = row.path

    df_images.dropna(axis=0, how='all', inplace=True)

    return df_images
