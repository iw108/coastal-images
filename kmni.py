# -*- coding: utf-8 -*-
"""
Created on Fri Feb  9 16:21:55 2018

@author: isaacwilliams


"""


import pandas as pd
import numpy as np
import netCDF4
from datetime import datetime, timedelta
import requests
import pytz
from utils import parse_datetime



_CATALOG =  'http://opendap.deltares.nl/thredds/dodsC/opendap/knmi/uurgeg/catalog.nc'


def get_stations(output = 'json'):
    """ Return list of kmni stations. Each station as dictionary containing site id, name lat and lon"""

    # Extract sites ids, long names, lat and long     
    with netCDF4.Dataset(_CATALOG, 'r') as ds:

        ids = [''.join([i.decode('utf-8') for i in item]) 
                    for item in ds['platform_id'][:].tolist()]
    
        names = [''.join([i.decode('utf-8') for i in item]).rstrip() 
                     for item in ds['platform_name'][:].tolist()]
    
        lats = ds['geospatialCoverage_northsouth_start'][0]
        lons = ds['geospatialCoverage_eastwest_start'][0]
    
        
    stations = [{'id': i, 'name': n, 'lat': lat, 'lon': lon} for i, n, lat, lon in zip(ids, names, lats, lons)]
    
    # remove duplicates
    stations = list({v['id']: v for v in stations}.values())
    
    if output is not 'json':
        stations = pd.DataFrame(stations)
        
    return stations




def get_data(stationID, tstart = None, tend = None, parameters = ['DD', 'FH'], to_pandas = True):

    
    if not tstart:
        tstart =  pytz.utc.localize(datetime.now())
    else:
        tstart = parse_datetime(tstart)
    tstart = tstart.replace(hour = 0)   


    if not tend:
        tend = pytz.utc.localize(datetime.now())
    else:
        tend = parse_datetime(tend)    
    tend = tend.replace(hour = 23)  
            
    
    # url to query                          
    url =  "http://projects.knmi.nl/klimatologie/uurgegevens/getdata_uur.cgi"
    
    
    # set up parameters
    dictionary = {'start':  tstart.strftime('%Y%m%d%H'), 'end':  tend.strftime('%Y%m%d%H'), 
                          'stns': stationID, 'vars': (':').join(parameters)}    
 
    text = requests.post(url, dictionary).text
    
    if to_pandas is False:
        return text
    
    else:
        
        df = process_kmni_txt(text)
        return df

    
          
def process_kmni_txt(text):
    
    # Seperate the request by lines 
    lines = text.split('\n')[:-1]
    header, values = [], []
    
    for line in lines:
        if line.startswith('#'):
            header.append(line.rstrip())        
        else:
            
            values.append([int(col) if col else None for col in line.strip().split(',')])

        
    columns = [column.strip() for column in header[-2].strip('#').split(',')]       
    
    if values:
               
        values = np.asarray(values).T
        data = {col: values[i] for i, col in enumerate(columns)}
    
        dates = []
        for yyyymmdd, hour in zip(data['YYYYMMDD'], data['HH']):
            date = datetime.strptime('{:.0f}'.format(yyyymmdd), "%Y%m%d")
            date += timedelta(hours = int(hour))
            dates.append(date)
        
        # Insert correct timestamp ...
        dates = [pytz.utc.localize(d) for d in dates]   
        df = pd.DataFrame({k:v for k, v in data.items() if k not in ['YYYYMMDD', 'HH', 'STN']}, index = dates)
            
    else:
        df = pd.DataFrame(columns = list(set(columns) - set(['YYYYMMDD', 'HH', 'STN'])))
    
    return df




if __name__ == '__main__':
    
    
    import matplotlib.pyplot as plt
    
    
    df = get_data(330, tstart = datetime(2014, 1, 1), tend = datetime(2014, 1, 1))
    
    plt.figure()
    plt.plot(df.FH/10, 'k')
    plt.xlabel('date')
    plt.ylabel('wind speed (m/s)')



