#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  5 12:16:35 2018

@author: williamsia
"""

from datetime import datetime
import pytz



def parse_datetime(dt):

    if not isinstance(dt, datetime):
        raise TypeError('Input must be of type datetime.datetime')

    if not dt.tzinfo:
        dt = pytz.utc.localize(dt)
    else:
        dt = dt.astimezone(pytz.utc)

    return dt


def parse_dates(tstart, tend):

    #Prepare start/end time
    if not tstart:
        tstart = pytz.utc.localize(datetime(2013, 10, 10))
    else:
        tstart = parse_datetime(tstart)

    if not tend:
        tend = pytz.utc.localize(datetime.now())
    else:
        tend = parse_datetime(tend)

    return tstart, tend


def ts2dt(dt):
    return pytz.utc.localize(datetime.utcfromtimestamp(dt))