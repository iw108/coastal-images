# -*- coding: utf-8 -*-
"""
Created on Fri Feb  9 16:01:29 2018

@author: isaacwilliams
"""


import numpy as np
import netCDF4
import pandas as pd
import requests
import re
from datetime import datetime
import pytz
from calendar import timegm


def get_stations(add_coords = False):

    url = ('http://live.waterbase.nl/waterbase_locaties.cfm?whichform=1&wbwns1='
            '1%7CWaterhoogte+in+cm+t.o.v.+normaal+amsterdams+peil+in+oppervlaktewater&wbthemas=&search=')
    f = requests.get(url).text
    sites = re.findall('\<option value="(.*)\</option\>', f)    
    station_list = [{'name': item.split(">")[1],  'id': item.split(">")[0][0: -1]} for item in sites]

    # adding coords is really slow ...
    if add_coords:
        for i, stn in enumerate(station_list):
            station_list[i].update(get_coordinates(stn['id']))
            
    return station_list



def get_coordinates(stationID):
    """
    Function gets the coordinates of tidal stations in the Netherlands from
    waterbase.nl website
    Input:
        site_id = list of site id's
    Output:
        coords = coordinates of site(s) as 2d array
        system = corresponding coordinate system     
    """
    
    # Url to query
    baseurl = ('http://live.waterbase.nl/metis/cgi-bin/'
                   'mivd.pl?action=value&format=xml&lang=nl&order=code&type=loc&code=')
    
    xml = requests.get(''.join((baseurl, stationID))).text
        
    # process request and extract coords and system
    coordsystem = int(re.findall('srsName="EPSG:(.*)">', xml)[0])  
    coords = re.findall('\<gml:Coordinates>(.*)\</gml:Coordinates\>', xml)[0]
    lon, lat = [*map(float, coords.split(','))]    

    return {'lon': lon, 'lat': lat, 'epsg': coordsystem}   






def get_data(stationID, tstart = None, tend = None):

    if not tstart:
        tstart =  pytz.utc.localize(datetime(2000, 1, 1))
    else:
        tstart = parse_datetime(tstart)
    

    if not tend:
        tend = datetime.datetime.now()
    else:
        tend = parse_datetime(tend)
            
    
    url = ('http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/waterbase'
              '/27_Waterhoogte_in_cm_t.o.v._normaal_amsterdams_peil_in_oppervlaktewater/nc/')    
    file = 'id1-{}.nc'.format(stationID)   

    
    with netCDF4.Dataset(''.join([url, file]) , 'r') as ds:
        t  = ds['time'][:]
        t = np.round(t*24*60)*60 - 3600
        mask = (t >= timegm(tstart.timetuple())) & (t  <= timegm(tend.timetuple()))
        
        sea_surface = ds['sea_surface_height'][:].flatten()[mask]

    return pd.DataFrame(sea_surface, index = map(lambda ts: pytz.utc.localize(datetime.utcfromtimestamp(ts)), t[mask]), columns = ['nu'])



if __name__ == '__main__':
    
    import matplotlib.pyplot as plt
    
    df = get_data('SCHEVNGN', tstart = datetime(2014, 1, 1), tend = datetime(2014, 1, 7))
    
    
    plt.figure()
    plt.plot(df.nu, 'k')
    plt.ylabel('tidal level (m)')
    plt.xlabel('date')
    
    
    
    




