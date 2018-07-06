#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 10:47:14 2018

@author: williamsia
"""

import numpy as np
import requests
import pandas as pd
import itertools
from datetime import datetime
from calendar import timegm
import pytz
import os
import json
from collections import OrderedDict
from utils import Wrapper



_CATALOG = "http://argus-public.deltares.nl/catalog"
_BASEPATH = "http://argus-public.deltares.nl/sites"


def get_sites():
    
    try:
        sites = requests.get(_CATALOG, {'output': 'json'}).json()
    
    except requests.ConnectionError:        
        print("Can't connect to server")
        sites = []

    return sites


def get_images(site_name, cameras = [], types = [], t = [], to_pandas = False):
    
    try:
        
        sites = requests.get(_CATALOG, {'output': 'json'}).json()
        site_info = [site for site in sites if site['site'] == site_name]
        
        if not site_info:
            print("Site doesn't exist.")
            return []
         
         
        if not t:
            t = [site_info[0]['startEpoch'], site_info[0]['endEpoch']] 
        else:
            t = [timegm(i.timetuple()) for i in t]

            
        # divide time into series of intervals
        interval = 30*24*3600 # approx a month
        tsteps = np.append(np.arange(t[0], t[1], interval), t[1])
        
            
        # Work around ...       
        dictionary_inserts = {}
        insert = {k: v for k, v in {'type': types, 'camera': cameras}.items() if v}
        if insert:
            keys = sorted(insert.keys())
            combos = list(itertools.product(*[insert[key] for key in keys]))
            dictionary_inserts = [{k: combo[i] for i, k in enumerate(keys)} for combo in combos]
                
        #Extract the images
        data = []
        for tstart, tend in zip(tsteps[0: -1], tsteps[1 :]):
            dictionary = {'site': site_name, 'output':'json', 'startEpoch': tstart , 'endEpoch': tend}
            
            if not dictionary_inserts:
                data += requests.get(_CATALOG, dictionary).json()['data']
            else:
                for insert in dictionary_inserts:
                    dictionary.update(insert.copy())
                    data += requests.get(_CATALOG, dictionary).json()['data']
       
        if to_pandas:
            data =  image_request(data)


    
    except requests.ConnectionError:
        print("Can't connect to server")
        data = []
    
    return data



def image_request(data):
    
    df = pd.DataFrame(data)
    df.drop(df[((df.type == 'pan') | (df.type == 'stack') | (df.type == 'plan'))].index, inplace = True)

    df.index = [datetime.utcfromtimestamp(i) for i in df.epoch]
     
    
    # Make multicolumn dataframe
    cols = [(camera, image) for camera in df.camera.unique() for image in df.type.unique()]
    indices = pd.date_range(start = df.index.min().floor('1H'), 
                                  end = df.index.max().ceil('1H'), freq = '30T', tz = pytz.utc)
    
    df_images = pd.DataFrame(index = indices, 
                                columns = pd.MultiIndex.from_tuples(cols))

    # Now fill data frame
    for index, row in df.iterrows():
        
        delta = abs((df_images.index - pytz.utc.localize(index)).total_seconds())
        if delta.min() < 600:
           df_images.loc[df_images.index[delta.argmin()], (row.camera, row.type) ] = row.path
    

    df_images.dropna(axis = 0, how = 'all', inplace = True) 
    
    return df_images



if __name__ == "__main__":
    
    saveRaw = False

    rawPath = os.path.join(os.path.dirname(__file__), '../raw/images')
    savePath = os.path.join(os.path.dirname(__file__), '..')
    
    # Extract image list and save
    images = get_images(site_name = 'zandmotor', 
                           cameras = [1, 2, 3, 4], types = ['snap', 'timex'])
                          
    

    if saveRaw:
        with open(os.path.join(rawPath, 'zandmotor.txt'), 'w') as file:
            file.write(json.dumps(images))
    

    # make sql database
    imagedb = Wrapper(os.path.join(savePath, 'images2.db'))
    
    columns = [{'name': 'camera', 'type': 'INTEGER'},
               {'name': 'epoch', 'type': 'INTEGER'}, 
               {'name': 'type', 'type': 'TEXT'},
               {'name': 'path', 'type': 'TEXT'}]  
    imagedb.create_table('zandmotor', columns)
    
    
    store = []
    for image in images:
        d = OrderedDict()
        d['camera'] = image['camera']
        d['epoch'] = image['epoch']
        d['type'] = image['type']
        d['path'] = image['path']
         
        store.append(d)
        
    imagedb.insert_many('zandmotor', store)
    
    imagedb.__exit__()
     
     
     

        

    
    
    
    
    
