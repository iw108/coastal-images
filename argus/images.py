#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 10:47:14 2018

@author: williamsia
"""

from calendar import timegm
from datetime import datetime
import itertools
import urllib
import requests

import cv2
import numpy as np
import pandas as pd
import pytz

from .settings import IMAGE_BASIC_TYPES, IMAGE_SITES, IMAGE_CATALOG_URL, IMAGE_SITES


def timestamp_from_datetime(date_time):
    return timegm(date_time.timetuple())


def parse_image_types(image_types):
    if isinstance(image_types, str):
        image_types = [image_types]
    if not (isinstance(image_types, list) and
            all([image_type in IMAGE_BASIC_TYPES for image_type in image_types])):
        raise ValueError('image_types must be string or list of strings')
    return image_types


def parse_camera_types(site, cameras):

    if not IMAGE_SITES.get(site, None):
        raise ValueError('Site does not exist')

    available_cameras = IMAGE_SITES[site]['cameras']

    # parse the selected cameras
    if isinstance(cameras, int):
        cameras = [cameras]
    if not (isinstance(cameras, list) and
            all([camera in available_cameras for camera in cameras])):
        raise ValueError('Camera must be integer or list of integers')
    return cameras


def get_images(time_start, time_end, parse=True, **kwargs):

    site = 'zandmotor'

    # parse the selected image types
    image_types = kwargs.get('image_types', [])
    if image_types:
        image_types = parse_image_types(image_types)

    # parse selected cameras
    cameras = kwargs.get('cameras', [])
    if cameras:
        cameras = parse_camera_types(site, cameras)

    # contruct options
    options = {'type': image_types, 'camera': cameras}
    options = {key: value for key, value in options.items() if value}
    if options:
        keys = sorted(options.keys())
        combinations = list(itertools.product(*[options[key] for key in keys]))
        option_list = []
        for combination in combinations:
            option_list.append(
                {key: combination[index] for index, key in enumerate(keys)}
            )

    # convert datetime to timestamps
    time_start = timestamp_from_datetime(time_start)
    time_end = timestamp_from_datetime(time_end)

    # split timestamps into intervals
    time_steps = np.linspace(
        time_start, time_end, max(2, int((time_end - time_start)/ (30 * 24 * 3600)))
    ).astype(int)


    parameters = {
        'site': 'zandmotor',
        'output':'json'
    }
    data = []
    for start_interval, end_interval in zip(time_steps[:-1], time_steps[1:]):
        parameters.update({
            'startEpoch': start_interval,
            'endEpoch': end_interval
        })
        if options:
            for item in option_list:
                parameters.update(item)
                data += requests.get(IMAGE_CATALOG_URL, parameters).json()['data']
        else:
            data += requests.get(IMAGE_CATALOG_URL, parameters).json()['data']

    # clean the output
    data = [item for item in data if item['type'] in IMAGE_BASIC_TYPES]

    if parse:
        return image_request_to_pandas(data)
    return data


def image_request_to_pandas(data):

    df = pd.DataFrame(data).set_index('epoch')
    df.index = df.index.map(
        lambda timestamp: datetime.utcfromtimestamp(timestamp)
    )

    # get unique cameras and image types from dataframe
    cameras = df.camera.unique()
    image_types = df.type.unique()
    to_multi_index = True if len(cameras) > 1 else False


    indices = pd.date_range(
        start=df.index.min().floor('1H'), end=df.index.max().ceil('1H'),
        freq='30T', tz=pytz.utc
    )

    # create empty dataframe to fill
    if not to_multi_index:
        columns = df.type.unique()
    else:
        columns = pd.MultiIndex.from_tuples(
            [(camera, image) for camera in cameras for image in image_types]
        )
    df_images = pd.DataFrame(index=indices, columns=columns)


    for index, row in df.iterrows():
        time_delta = abs((df_images.index - pytz.utc.localize(index)))\
                         .total_seconds()
        if time_delta.min() < 600:
            index = df_images.index[time_delta.argmin()]
            if to_multi_index:
                df_images.loc[index, (row.camera, row.type)] = row.path
            else:
                df_images.loc[index, row.type] = row.path
    df_images.dropna(axis=0, how='all', inplace=True)
    return df_images


def load_image(url, to_float=True):

    response = urllib.request.urlopen(url)

    image_bytes = np.asarray(bytearray(response.read()), dtype="uint8")

    image = cv2.cvtColor(
        cv2.imdecode(image_bytes, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB
    )
    if to_float:
        return np.float32(image.astype(float)/255)
    return image
