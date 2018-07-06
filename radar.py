#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  5 16:46:21 2018

@author: williamsia
"""



import netCDF4
import numpy as np
import pandas as pd
from datetime import datetime
from calendar import timegm
import urllib
import re
import os
from projections import Projection
from utils import ts2dt


_BASEURL = 'http://opendap.knmi.nl/knmi/thredds'
_CATALOG = os.path.join(_BASEURL, 'catalog')
_OPENDAP = os.path.join(_BASEURL, 'dodsC')
_DIRS = 'radarprecipclim/RAD_NL25_RAC_MFBS_5min_NC'


def _get_catalog(*args):
    return os.path.join(_CATALOG, *args, 'catalog.html')


def available_years():
    
    urlpath =urllib.request.urlopen(_get_catalog(_DIRS))
    string = urlpath.read().decode('utf-8')
    
    pattern = re.compile("'([0-9]{4})/catalog.html'")
    years = pattern.findall(string)
    
    return  years


def available_months(year):    
    try:
        urlpath =urllib.request.urlopen(_get_catalog(_DIRS, str(year)))
        string = urlpath.read().decode('utf-8')
    
        pattern = re.compile("'([0-9]{2})/catalog.html'")
        months = pattern.findall(string)
    
    except urllib.request.HTTPError:    
        months = []
    
    return months


def available_files(year, month):    
    
    try:
        urlpath =urllib.request.urlopen(_get_catalog(_DIRS, '{:04d}'.format(year), '{:02d}'.format(month)))
        string = urlpath.read().decode('utf-8')    

        pattern = re.compile("(?<=dataset=)(.*)(?=')")
        files = pattern.findall(string) 
        files = [os.path.join(_OPENDAP, file) for file in files if file.endswith('.nc')]  
    
    except urllib.request.HTTPError:
    
         files = []
    
    return files



def get_precip(lon, lat, tstart, tend):
        
    dates = pd.date_range(tstart, tend, freq = 'M')
    if dates.empty:
        dates = [tstart]
    
    timestamps, precip, redo = [], [], []
    for date in dates:
        
        files = available_files(date.year, date.month)
        
        if not files:
            continue
        
        tsFull = map(lambda file: datetime.strptime(file.split('_')[-1], '%Y%m%d%H%S.nc'), files)
        files = [file for file, ts in zip(files, tsFull) if ts >= tstart and ts <= tend]
        
        for file in files:              
            try:
                with netCDF4.Dataset(file, 'r') as ds:
             
                    timestamps += ds['time'][:].tolist()
     
                    proj = Projection( "+init=EPSG:28992", 
                                               ds['projection'].proj4_params)     
                    
                    origin = proj.forwards([lon], [lat])
    
                    xx, yy = np.meshgrid(ds['x'][:], ds['y'][:] )
                    row, col = np.unravel_index(np.sqrt((xx - origin[0])**2 + (yy - origin[1])**2).argmin(), xx.shape)
           
                    precip += [ds['image1_image_data'][0, row, col]]
                
            except OSError:
                redo += [file]

    if timestamps:                
        timestamps = np.asarray(timestamps) + timegm(datetime(2000, 1, 1).timetuple())   
        df = pd.DataFrame(precip, index = [*map(lambda t: ts2dt(t), timestamps)], 
                                                columns = ['precip'])
    else:
        df = pd.DataFrame(columns = 'precip')
        
    return df
    


if __name__ == '__main__':
    
    import matplotlib.pyplot as plt
    
    df = get_precip(72502, 452074, datetime(2014, 1, 1), datetime(2014, 1, 2))
    
    plt.figure()
    plt.plot(df, 'k')
    
    
    

        