# -*- coding: utf-8 -*-
"""
Created on Mon Apr 30 13:51:09 2018

@author: isaacwilliams
"""

import netCDF4
import pytz
from datetime import datetime
import numpy as np
import pandas as pd
from calendar import timegm
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from utils import parse_datetime, parse_dates, ts2dt



_GPSFILE = ('http://opendap.tudelft.nl/thredds/dodsC/data2/zandmotor/'
                    'morphology/JETSKI/surveypath/jetski_surveypath.nc')

_LIDARFILE = ('http://opendap.deltares.nl/thredds/dodsC/'
                    'opendap/rijkswaterstaat/kusthoogte/30dz1.nc')

_PRECIPFILE = '/Users/williamsia/surfdrive/data/zandmotor/radar/raw/radar.nc'


# _METEOFILE = ('http://opendap.tudelft.nl/thredds/dodsC/'
#                         'data2/zandmotor/meteohydro/meteo/meteo/meteo.nc')

_METEOFILE = '/Users/williamsia/surfdrive/streamers/zandmotor/data/meteo.nc'

                      
_METEOVARIABLES = ['AirTemp_Avg', 'RelHumid_Avg', 'AirTemp_Avg', 
                     'SolarRad_Avg',  'Rainfall_Tot', 'WindSpeed_Avg', 'Barometer_Avg',
                        'WindDir_Avg', 'WindSpeed_Min', 'WindSpeed_Max', 'WindDir_Std']





def get_meteo(tstart = None, tend = None, variables = ['WindSpeed_Avg', 'WindDir_Avg']):
                   
    tstart, tend = parse_dates(tstart, tend)


    #Get selected variables
    variables = [var for var in variables if var in _METEOVARIABLES]
     
     
    # Open file and extract            
    with netCDF4.Dataset(_METEOFILE, 'r') as ds:         
        t = np.asarray(ds['time'][:])
        
        mask = (t >= timegm(tstart.timetuple())) & (t  <= timegm(tend.timetuple()))
        data = {v: ds.variables[v][mask] for v in variables}
                
                
    return pd.DataFrame(data, index = map(lambda ts: ts2dt(ts), t[mask]))



def get_precipitation(tstart = None, tend = None):
    
    tstart, tend = parse_dates(tstart, tend)
        
    with netCDF4.Dataset(_PRECIPFILE, 'r') as ds:
        
        t = ds['time'][:]
        mask = (t >= timegm(tstart.timetuple())) & (t  <= timegm(tend.timetuple()))
    
        data = ds['precip'][mask]
    
    return pd.DataFrame(data, index = map(lambda t: ts2dt(t), t[mask]), columns = ['precip'])


#------------------------------------------------------------------------------
#              Groundwater   
#------------------------------------------------------------------------------ 

def read_groundwater(fname):

    with open(fname, 'rb') as f:
   
        header = {}
        for i in range(7):
            line = f.readline().decode().strip('\r\n').split(';')
        
            if len(line) == 2:
                header[line[0]] = line[1]
    
    
        columns = f.readline().decode().strip(';\r\n').split(';')[3:]
    
    
        fmt = '%d-%m-%Y %H:%M:%S'
        timestamp, data = [], []
        for line in f:
            line = line.decode().strip(';\r\n').split(';')[1:]
                   
            timestamp.append(datetime.strptime(' '.join((line[0],line[1])), fmt))
            data.append([*map(np.float32, line[2:])])
        
    df = pd.DataFrame(data, index = timestamp, columns = columns)
    df.sort_index(inplace = True)

    return df, header


#------------------------------------------------------------------------------
#       Functions for resampling data frames   
#------------------------------------------------------------------------------  

def direction(x):
    if np.sum(np.isnan(x)) == 0:
        x = np.deg2rad(x)
        
        east = np.sin(x).mean()
        west = np.cos(x).mean()    

        theta = np.arctan2(east, west) % (2*np.pi)
        theta = np.mean(np.rad2deg(theta))
    
    else:
        theta = np.nan        
    return theta


def mean(x):
    if np.sum(np.isnan(x)) == 0:
        out = np.mean(x)
    else:
        out = np.nan       
    return out


#------------------------------------------------------------------------------
#                   topo   
#------------------------------------------------------------------------------ 

def topo_timestamps(method = 'lidar'):
    
    file = _GPSFILE
    if method.lower() == 'lidar':
        file = _LIDARFILE
    
    with netCDF4.Dataset(file, 'r') as ds:
        time = ds['time'][:]*24*60*60
        dates = list(map(lambda t: pytz.utc.localize(datetime.utcfromtimestamp(t)), time))
            
    return dates    
    
  
def get_lidar(date):    
    
    if not date.tzinfo:
        date = pytz.utc.localize(date)
    else:
        date = date.astimezone(pytz.utc)
        
    
    with netCDF4.Dataset(_LIDARFILE, 'r') as ds:
        
        time = ds['time'][:]*24*60*60
        datesLIDAR = list(map(lambda t: pytz.utc.localize(datetime.utcfromtimestamp(t)), time))
        
        idx = abs(datesLIDAR - date).argmin()
        
        x, y, z = ds['x'][:], ds['y'][:], ds['z'][idx]  
        
        return x, y, z, datesLIDAR[idx]
 
       
                
def get_gps(date, to_grid = False, xlims = (70000, 75000), ylims = (450000, 455000), dx = 2, dy = 2):

    date = parse_datetime(date)  
    

    with netCDF4.Dataset(_GPSFILE, 'r') as ds:
        
        time = ds['time'][:]*24*60*60
        datesGPS = list(map(lambda t: ts2dt(t), time))
        
        idx = abs(np.asarray(datesGPS) - date).argmin()
        
        xyz = ds['survey_path_RD'][idx]
        x, y, z = xyz[xyz.mask[:,0] == False, :].data.T
    

    if to_grid == True:
        xx, yy  = np.meshgrid(np.arange(*xlims, dx), np.arange(*ylims, dy))
        zz = griddata((x, y), z, (xx, yy))        
        
        x, y, z = xx[0, :], yy[:, 0], zz
        
    return x, y, z, datesGPS[idx]
    



def loadlidartxt(file_name, xlims = None, ylims = None):
    """"
    Function loads lidar survey stored in .txt format
    Inputs:
        file_name = file name of Lidar surveys
    Outputs:
        xx = x grid (2d array)
        yy = y grid (2d array)
        zz = elevation (2d array)

    """ 
    with open(file_name, 'r') as f:
        headers = {}
        for i in range(6):
            name, val = f.readline().split()
            headers[name.lower()] = int(val)
        data = np.zeros((headers['nrows'], headers['ncols']))
        for i, line in enumerate(f):
            items = line.strip().split()
            if not items:
                continue
            data[i, :] = list(map(float, items))
            
    data[data == headers['nodata_value']] = np.nan
    data = data[:: -1]/100 # from cm to m
    
    """ make mesh grid """
    xRD = np.arange(headers['xllcorner'], headers['xllcorner'] + (headers['ncols'])*headers['cellsize'], headers['cellsize'])
    yRD = np.arange(headers['yllcorner'], headers['yllcorner'] + (headers['nrows'])*headers['cellsize'], headers['cellsize'])

    
    if xlims:
        col_crop =  (xRD >= min(xlims)) & (xRD <= max(xlims))
        xRD = xRD[col_crop]
        data = data[:, col_crop]
    
    if ylims:
        row_crop =  (yRD >= min(ylims)) & (yRD <= max(ylims))
        yRD = yRD[row_crop]
        data = data[row_crop, :] 
        
    return xRD, yRD, data



class XYTree(object):
    """ 
    class for quick nearest neighbour searches for topo
    """

    def __init__(self, x, y, z):  
        
        x, y, z = self._parse_input(x, y, z)
        
        self._xytree = cKDTree(np.column_stack((x.ravel(), y.ravel())))
        self._z = z


    @property
    def xyz(self):
        return np.column_stack((self._xytree.data, self._z))

       
    def get_z(self, x, y):
        ind = self._xytree.query(np.column_stack((x.ravel(), y.ravel())))[1]
        return self._z[ind]


    @staticmethod
    def _parse_input(x, y, z):
        
        if not isinstance(x, np.ndarray) or not isinstance(y, np.ndarray) or not isinstance(z, np.ndarray):
            raise TypeError('Inputs should be of type numpy.ndarray')
        
        if len(set([x.size, y.size, z.size])) != 1:
            raise ValueError('Input arrays should all have same size')
              
        x, y, z = x.flatten(), y.flatten(), z.flatten()
        
        mask = ~np.isnan(x) & ~np.isnan(y) & ~np.isnan(z)
        
        return x[mask], y[mask], z[mask]  








if __name__ == '__main__':
   
    
   import matplotlib.pyplot as plt
   
   x, y, z = get_gps(datetime(2014, 1, 1), to_grid = True)[0: -1]
   
   extent = x.min(), x.max(), y.min(), y.max()
   
   plt.figure()
   plt.imshow(z[::-1], extent = extent)
   plt.xlabel('xRD')
   plt.ylabel('yRD')
   

   df = get_meteo(tstart = datetime(2013, 11, 1), tend = datetime(2013, 11, 2))                 
   df = df.resample('10T', label = 'right', closed = 'right').agg({'WindDir_Avg': direction, 'WindSpeed_Avg': mean})


   f, (ax1, ax2) = plt.subplots(2, 1)
   ax1.plot(df.WindDir_Avg, 'k')
   ax1.set_ylim(0, 360)
   ax2.plot(df.WindSpeed_Avg, 'k')
   ax2.set_ylim(0, 20)

   
   ax1.set_ylabel('Wind direction (deg N)')
   ax2.set_ylabel('Wind speed (m)')
   ax2.set_xlabel('date')
   


