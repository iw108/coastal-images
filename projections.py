# -*- coding: utf-8 -*-
"""
Created on Fri Apr 27 07:36:00 2018

@author: isaacwilliams
"""

import pyproj
import numpy as np
import ephem
import pytz
from timezonefinder import TimezoneFinder


# x0, y0, rotation, coordsystem

tzfinder = TimezoneFinder() 



def pythag_dist(x, y, x0 = 0, y0 = 0):
    dist = ((np.asarray(x) - x0)**2 + (np.asarray(y) - y0)**2)**0.5  
    return dist 
    


class Argus:
    
    def __init__(self, x0, y0, rotation):
        self.x0 = x0
        self.y0 = y0
        self.phi = rotation       
       
    #Argus to local
    def toargus(self, x, y):  
        x, y, shape = self._parse_input(x, y)       
        coords = self._rotate(np.column_stack((x, y)) - [self.x0, self.y0]) 
        return coords[:, 0].reshape(shape), coords[:, 1].reshape(shape)
    
    
    #Local to argus
    def tolocal(self, x, y):
        x, y, shape = self._parse_input(x, y)
        coords = self._rotate(np.column_stack((x, y)), positive = False) + [self.x0, self.y0]
        return coords[:, 0].reshape(shape), coords[:, 1].reshape(shape)
        
           
    def _rotate(self, xy, positive = True):     
        if not positive:
            theta = np.deg2rad(-self.phi)
        else:
            theta = np.deg2rad(self.phi)
            
        rotMatrix = np.array([[np.cos(theta), np.sin(theta)], 
                                           [-np.sin(theta), np.cos(theta)]])
        xy = np.dot(rotMatrix, xy.T).T   
        return xy
    
    
    @staticmethod
    def _parse_input(x, y):
        if not isinstance (x, (list, np.ndarray)) and not isinstance (y, (list, np.ndarray)):
            raise ValueError('Must be of type list | numpy.ndarray')

        x, y = np.asarray(x), np.asarray(y)
            
        if x.shape != y.shape:
            raise ValueError('Inputs not of same shape')
                
        
        return x.flatten(), y.flatten(), x.shape
    
    
class Projection:
    
    def __init__(self, p1, p2):
        self.p1 = pyproj.Proj(p1)
        self.p2 = pyproj.Proj(p2)
        
          
    def forwards(self, lon, lat):
        lon, lat, shape = self._parse_input(lon, lat)
        coords = np.asarray([pyproj.transform(self.p1, self.p2, i, j) for i, j in zip(lon, lat)])
        return coords[:, 0].reshape(shape), coords[:, 1].reshape(shape)


    def backwards(self, lon, lat):
        lon, lat, shape = self._parse_input(lon, lat)
        coords = np.asarray([pyproj.transform(self.p2, self.p1, i, j) for i, j in zip(lon, lat)])
        return coords[:, 0].reshape(shape), coords[:, 1].reshape(shape)
        
    
    @staticmethod
    def _parse_input(lon, lat):
        
        if not isinstance (lon, (list, np.ndarray)) and not isinstance (lat, (list, np.ndarray)):
            raise ValueError('Must be of type list | numpy.ndarray')

        lon, lat = np.asarray(lon), np.asarray(lat)
            
        if lon.shape != lat.shape:
            raise ValueError('Inputs not of same shape')
                
            
        return lon.flatten(), lat.flatten(), lon.shape



 



class Argusproj(Argus, Projection):
    
    def __init__(self, x0, y0, rotation, epsg):
        Argus.__init__(self, x0, y0, rotation)
        Projection.__init__(self, "+init=EPSG:{}".format(epsg), "+init=EPSG:4326")


    def origin(self, coordsystem = 'global'):
        if coordsystem == 'global':
        	x, y = self.forwards([self.x0], [self.y0])
        	x, y = x[0], y[0]
        
        elif coordsystem == 'local':
            x, y = self.x0, self.y0
        
        elif coordsystem == 'argus':
            x, y = 0., 0.

        return x, y
 


    def globaltoargus(self, x, y):
        x, y = self.local2argus(*self.backwards(x, y))
        return x, y


    def argustoglobal(self, x, y):
        x, y = self.forwards(*self.argus2local(x, y))
        return x, y



    
class Solar:
    
    _Obs = ephem.Observer()

    def __init__(self, lon, lat, elev = 0, mode = 'deg'):
        
        if mode == 'deg':
            lon_rad, lat_rad = map(lambda x: x*np.pi/180, [lon, lat])
            lon_deg, lat_deg = lon, lat
        else:
            lon_deg, lat_deg = map(lambda x: x*180/np.pi, [lon, lat])
            lon_rad, lat_rad = lon, lat
 
        self._Obs.lon = lon_rad
        self._Obs.lat = lat_rad 
        self._Obs.elev = elev
      
        timezone = tzfinder.timezone_at(lng = lon_deg, lat = lat_deg)                 
        self.tz =  pytz.timezone(timezone)                           
            

    def sun_position(self, date, output = 'rad'):

        self._Obs.date = self._process_input_date(date)
        position = ephem.Sun(self._Obs)
        position.compute(self._Obs)
        
        azimuth, altitude = position.az, position.alt
        
        if output == 'deg':
            azimuth, altitude = map(lambda x: x*180/np.pi, [altitude, azimuth])
        
        return position.az, position.alt
    
   
    def daylight_hours(self, date):
        
        date = date.replace(hour = 0, minute = 0, second = 0)

        input_date = self._process_input_date(date)
        self._Obs.date = input_date
        
        sunrise = self._Obs.next_rising(ephem.Sun()).datetime()        
        sunset = self._Obs.next_setting(ephem.Sun()).datetime()
        
        return self._process_output_date(sunrise), self._process_output_date(sunset)


    def _process_output_date(self, date):
        date = pytz.utc.localize(date)
        return date.astimezone(self.tz)
        

    def _process_input_date(self, date):
        
        if not date.tzinfo:
            date = self.tz.localize(date)

        return date.astimezone(pytz.utc)

        
    
def rotate(phi, xy):
    
    rotMatrix = np.array([[np.cos(phi), np.sin(phi)], 
                         [-np.sin(phi), np.cos(phi)]])
    xy = np.dot(rotMatrix, xy.T).T   
    
    return xy  



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
