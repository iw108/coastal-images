#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 09:25:49 2018

@author: williamsia
"""


import numpy as np
import requests
from collections import OrderedDict
import os
import json
from utils import Wrapper



_URL = 'http://argus-public.deltares.nl/db/table'

def available_tables():
    return list(set(requests.get(_URL).json()) - set(['autoGeom', 'usedTemplate'])) 


def get_db(tables = []):    

    try:               
        if tables:
            tables = [table for table in tables if table in available_tables()]
        else:
            tables = available_tables()
           
            
        if tables:       
            argusdb = {k : requests.get(('/').join([_URL, k])).json() for k in tables}
        else:
            print('Valid table not selected')
            argusdb = {}
            
           
    except requests.ConnectionError:
        print("Can't connect to server")
        argusdb = {}
        
    return argusdb



if __name__ == "__main__":
    
    rawpath = os.path.join(os.path.dirname(__file__), '../raw')
    processedpath = os.path.join(os.path.dirname(__file__), '../processed')


    # extract database and save locally
    tables = get_db()

    for key in tables.keys():
        fname = '{}.txt'.format(key)   
    
        with open(os.path.join(rawpath, fname), 'w') as file:
            file.write(json.dumps(tables[key]))


    # make sql database

    argusdb = Wrapper(processedpath)

    columns = [{'name': 'seq', 'type': 'INTEGER'},
               {'name': 'siteID', 'type': 'TEXT'}, 
               {'name': 'name', 'type': 'TEXT'},
               {'name': 'TZname', 'type': 'TEXT'}, 
               {'name': 'TZoffset', 'type': 'INTEGER'},
               {'name': 'x', 'type': 'REAL'},  
               {'name': 'y', 'type': 'REAL'},
               {'name': 'rotation', 'type': 'REAL'}, 
               {'name': 'EPSG', 'type': 'TEXT'}, 
               {'name': 'degFromN', 'type': 'REAL'}]  
                 
    values = []              
    for site in tables['site']:

        if site['coordinateOrigin']:
            x, y = site['coordinateOrigin'][0][0:-1]
        else:
            x, y = None, None
        
        d = OrderedDict()
        d['seq'] = site['seq']
        d['siteID'] = site['id']
        d['name'] =  site['siteID'].lower()
        d['TZname']  = site['TZName']
        d['TZoffset'] = site['TZoffset']
        d['x'] = x
        d['y'] = y
        d['rotation'] = site['coordinateRotation']
        d['EPSG'] = site['coordinateEPSG']
        d['degFromN'] = site['degFromN'] 
        values.append(d)
        
    
    argusdb.create_table('site', columns)
    argusdb.insert_many('site', values) 

    ## -----------------------------------------------------------------------------
    ##                       Make station table
    ## -----------------------------------------------------------------------------
                    
    columns = [{'name': 'seq', 'type': 'INETGER'},
               {'name': 'stnID', 'type': 'TEXT'}, 
               {'name': 'siteID', 'type': 'TEXT '},
               {'name': 'timeIN', 'type': 'INTEGER'},
               {'name': 'timeOUT', 'type': 'INTEGER'}]


    values = []
    for stn in tables['station']:
    
        d = OrderedDict()
        d['seq'] = stn['seq']
        d['stnID'] = stn['id']
        d['siteID'] = stn['siteID']
        d['timeIN'] = stn['timeIN']
        d['timeOUT'] = stn['timeOUT']
    
        values.append(d)

    
    argusdb.create_table('station', columns)
    argusdb.insert_many('station', values)


    ## -----------------------------------------------------------------------------
    ##                Make camera table
    ## ----------------------------------------------------------------------------- 

    image_dims = np.array([[2448, 2048], [1392, 1040], [1024, 768], [640, 480]])
 
    columns = [{'name': 'seq', 'type': 'INTEGER'},
               {'name': 'camID', 'type': 'TEXT'}, 
               {'name': 'stnID', 'type': 'TEXT '},
               {'name': 'camNumber', 'type': 'INTEGER'},
               {'name': 'fx', 'type': 'REAL'},
               {'name': 'fy', 'type': 'REAL'},
               {'name': 'cx', 'type': 'REAL'},
               {'name': 'cy', 'type': 'REAL'},
               {'name': 's', 'type': 'REAL'},
               {'name': 'k1', 'type': 'REAL'},
               {'name': 'k2', 'type': 'REAL'},
               {'name': 'k3', 'type': 'REAL'},
               {'name': 'k4', 'type': 'REAL'},
               {'name': 'p1', 'type': 'REAL'},
               {'name': 'p2', 'type': 'REAL'},
               {'name': 'Nu', 'type': 'INTEGER'},
               {'name': 'Nv', 'type': 'INTEGER'},
               {'name': 'x', 'type': 'REAL'},
               {'name': 'y', 'type': 'REAL'},
               {'name': 'z', 'type': 'REAL'}]
             
    values = []
    for cam in tables['camera']:   
   
        K = np.abs(np.asarray(cam['K']).T)    
        if K.shape == (3, 3):
            fx, fy = K[0, 0], K[1, 1]
            cx, cy = K[0, 2], K[1, 2]
            s = K[0, 1]
        else:
            fx, fy, cx, cy, s = None, None, None, None, None
    
        k1, k2, k3, k4 = cam['Drad'][0]
        p1, p2 = 0., 0.
        Nu, Nv = [*map(int, image_dims[((image_dims - [2*cam['D_U0'], 2*cam['D_V0']])**2).sum(axis = 1).argmin()])]
         
        d = OrderedDict()
        d['seq'] = cam['seq']
        d['camID'] = cam['id']
        d['stnID'] = cam['stationID']
        d['camNumber'] = cam['cameraNumber']
        d['fx'] = fx
        d['fy'] = fy
        d['cx'] = cx
        d['cy'] = cy
        d['s'] = s
        d['k1'] = k1
        d['k2'] = k2
        d['k3'] = k3
        d['k4'] = k4
        d['p1'] = p1
        d['p2'] = p2
        d['Nu'] = Nu
        d['Nv'] = Nv
        d['x'] = cam['x']
        d['y'] = cam['y']
        d['z'] = cam['z']
    
        values.append(d)   


    argusdb.create_table('camera', columns)
    argusdb.insert_many('camera', values)


    ## -----------------------------------------------------------------------------
    ##                       Make gcp table
    ## -----------------------------------------------------------------------------

    columns = [{'name': 'seq', 'type': 'INTEGER'},
               {'name': 'gcpID', 'type': 'TEXT'},
               {'name': 'siteID', 'type': 'TEXT'},
               {'name': 'x', 'type': 'REAL'},
               {'name': 'y', 'type': 'REAL'},
               {'name': 'z', 'type': 'REAL'}] 

    values = []
    for gcp in tables['gcp']: 
    
        d = OrderedDict()
        d['seq'] = gcp['seq']
        d['gcpID'] = gcp['id']
        d['siteID'] = gcp['siteID']
        d['x'] = gcp['x']
        d['y'] = gcp['y']
        d['z'] = gcp['z']
    
        values.append(d)   

    argusdb.create_table('gcp', columns)
    argusdb.insert_many('gcp', values)


    ## -----------------------------------------------------------------------------
    ##                       Make used table
    ## -----------------------------------------------------------------------------         
        
    columns = [{'name': 'seq', 'type': 'INTEGER'},
               {'name': 'geomID', 'type': 'INTEGER'},
               {'name': 'gcpID', 'type': 'TEXT'},
               {'name': 'u', 'type': 'REAL'},
               {'name': 'v', 'type': 'REAL'}]     

    values = []
    for gcp in tables['usedGCP']:
        
        d = OrderedDict()
        d['seq'] = gcp['seq']
        d['geomID'] = gcp['geometrySequence']
        d['gcpID'] = gcp['gcpID']
        d['u'] = gcp['U']
        d['v'] = gcp['V']
    
        values.append(d)   
    
    argusdb.create_table('usedGCP', columns)
    argusdb.insert_many('usedGCP', values)


    ## -----------------------------------------------------------------------------
    ##                       Make geometry table
    ## -----------------------------------------------------------------------------

      
    columns = [{'name': 'geomID', 'type': 'INTEGER'},
               {'name': 'camID',  'type': 'TEXT'},
               {'name': 'valid',  'type': 'INTEGER'}]  
           
    values = []
    for geom in tables['geometry']: 
    
        d = OrderedDict()
        d['geomID'] = geom['seq']
        d['camID'] = geom['cameraID']
        d['valid'] = geom['whenValid']

        values.append(d)     
    
    
    argusdb.create_table('geometry', columns)
    argusdb.insert_many('geometry', values)
 

    argusdb.curs.execute('ALTER TABLE geometry ADD COLUMN gcpCounts INTEGER') 
    geomIDs = [geomID[0] for geomID in argusdb.query('SELECT geomID FROM geometry', output = 'none')]
    for geomID in geomIDs:
        query  = '''UPDATE geometry
                    SET gcpCounts = (SELECT COUNT(*) FROM usedGCP WHERE geomID={})
                    WHERE geomID = {} '''.format(geomID, geomID)
        argusdb.curs.execute(query)  
 
    argusdb.__exit__()
    








    
    
    
    
    
    








     
     