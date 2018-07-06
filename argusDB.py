#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 19 13:30:54 2018

@author: williamsia
"""


import pickle
import numpy as np
import sqlite3
import requests
from collections import OrderedDict
import pandas as pd
import itertools
from datetime import datetime
from calendar import timegm
import pytz



_dbpath = './local/db/'
_baseurl = "http://argus-public.deltares.nl/sites"


# SQL wrapper
class Wrapper:
    
    def __init__(self, name):
        self.conn = sqlite3.connect(name)
        self.curs = self.conn.cursor()    
        
 
    @property
    def tables(self):
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        return [table[0] for table in self.curs.execute(query).fetchall()]     
        
        
  
    def query(self, statement, output = 'pandas'):
            
        req = self.curs.execute(statement)
        cols = [col[0] for col in req.description]
        
        if output == 'json' :
            return [{k: v for k, v in zip(cols, vals)} for vals in req.fetchall()]        
        
        elif output == 'none':
            return req.fetchall()

        else:    
            return pd.DataFrame.from_records(req.fetchall(), columns = cols)            
            
            
    def create_table(self, table_name, columns):
        
        if table_name in self.tables:
            print('Table already exists')
        else:
            cols = ', '.join([' '.join([col['name'].strip(), col['type'].strip()]) for col in columns])
            statement = '''CREATE TABLE {} ({})'''.format(table_name, cols)
            self.curs.execute(statement)
            self.conn.commit()
            

    def insert_many(self, table_name, columns):
        tuples = [tuple([col[1] for col in v.items()]) for v in columns]   
        statement = 'INSERT INTO {} VALUES ({})'.format(table_name, ','.join(['?' for i in range(len(tuples[0]))]))
        self.curs.executemany(statement, tuples)
        self.conn.commit()

       
    def __exit__(self):
        self.conn.commit()
        self.conn.close()


# -----------------------------------------------------------------------------
#                        ImageDB
# -----------------------------------------------------------------------------


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



class Imagedb(Wrapper):
    
    
    def __init__(self, name = _dbpath + 'images.db'):
        Wrapper.__init__(self, name)
    
    
    def list_cameras(self, site):
        query = 'SELECT DISTINCT camera FROM {}'.format(site.lower())
        print('Cameras from :', [camera[0] for camera in self.query(query).fetchall()])



    def image_query(self, site, cameras = [], types = [], tlims = []):
    
    
        # Build query statement
        components = [' AND '.join(["camera={}".format(i) for i in cameras]),
                    ' OR '.join(["type=\'{}\'".format(i) for i in types])]
        
        if tlims:
            tunix = [timegm(t.timetuple()) for t in tlims]
            components.append('epoch >= {} AND epoch <= {}'.format(*tunix))

      
        components = [comp for comp in components if comp]
        if components:
            for i, comp in enumerate(components):
                if i == 0:
                    query = 'WHERE {}'.format(comp)
                else:
                    query = '{} AND ({})'.format(query, comp)
        else:
            query = ''
            
        query =  "SELECT * FROM {} {}".format(site, query)
        

        data = self.query(query, output = 'json')

        return image_request(data)
        

# =============================================================================
#                 argus db
# =============================================================================


class Argusdb(Wrapper):


    def __init__(self, name = _dbpath + 'argus.db'):
        Wrapper.__init__(self, name)

    
    # Get site info
    def get_site(self, name = '', siteID = '', output = 'json'):
        
        sql = ''
        if name:
            sql = """ SELECT * 
                      FROM site 
                      WHERE name=\'{}\'""".format(name)
        else:
            sql = """ SELECT * 
                      FROM site 
                      WHERE siteID=\'{}\'""".format(siteID)
        
        if not sql:
            sql = """ SELECT * 
                      FROM site """
                     
        return self.query(sql, output = output)

    
    # get camera station info
    def get_station (self, name = '', siteID = '', stnID = '', output = 'json'):
        
        sql = ''
        if name:
            sql = """ SELECT * 
                      FROM station
                      WHERE siteID=(SELECT siteID FROM site WHERE name=\'{}\')""".format(name)
        if siteID:
            sql = """ SELECT * 
                      FROM station 
                      WHERE siteID=\'{}\'""".format(siteID)
    
        if stnID:
            sql = """ SELECT * 
                      FROM station 
                      WHERE stnID = \'{}\'""".format(stnID)
        
        if not sql:
            sql = """ SELECT * 
                      FROM station """
        
        
        return self.query(sql, output = output)
    
    
    # get camera info
    def get_camera(self, name = '', siteID = '', stnID = '', camID = '', output = 'json', process = True):


        if process == True:    
            output = 'json'
        
        sql = ''
        if name:
            siteID = self.query("SELECT siteID FROM site WHERE name=\'{}\'".format(name), output = 'none')[0][0]

        if siteID:
            sql = """ SELECT * 
                      FROM camera 
                      WHERE camID LIKE '%{}%'""".format(siteID[0:3])

        if stnID:
            sql = """ SELECT * 
                      FROM camera 
                      WHERE stnID = \'{}\'""".format(stnID)  

        if camID:
            sql = """ SELECT * 
                      FROM camera 
                      WHERE camID = \'{}\'""".format(camID) 
        
        if not sql:
            sql = """ SELECT * 
                      FROM camera """
    
        cameras = self.query(sql, output = output)

        if process:
            processed = []
            for cam in cameras:
                processed.append({
                    'camID': cam['camID'],
                    'camNumber' : cam['camNumber'],
                    'stnID' : cam['stnID'],
                    'K' : np.array([[cam['fx'], cam['s'], cam['cx']], 
                                  [0, cam['fy'], cam['cy']], [0, 0, 1]]),
                    'xyz' : np.array([cam['x'], cam['y'], cam['z']]),
                    'Drad': np.array([cam['k1'], cam['k2'], cam['k3'], cam['k4']]),
                    'Dtan': np.array([cam['p1'], cam['p2']]),
                    'Nu'  : cam['Nu'],
                    'Nv'  : cam['Nv']
                })
            cameras = processed
        
        return cameras
        
            
    def get_geometry_list(self, camID, ngcps = 3):
        sql =  """ SELECT * FROM geometry
                   WHERE camID = \'{}\' AND gcpCounts >= {} 
                   ORDER BY valid""".format(camID, ngcps)
        return self.query(sql, output = 'pandas')
               

    def get_geometry(self, geomID, output = 'pandas'):
        
        sql =  """ SELECT usedGCP.gcpID AS gcpID, usedGCP.u As u, usedGCP.v AS v,
                                gcp.x AS x, gcp.y AS y, gcp.z as z 
                         FROM usedGCP
                         INNER JOIN gcp ON usedGCP.gcpID = gcp.gcpID
                         WHERE geomID={} """.format(geomID)
               
        return self.query(sql, output = output)

