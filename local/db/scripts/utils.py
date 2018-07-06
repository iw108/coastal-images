#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 11:31:21 2018

@author: williamsia
"""

import sqlite3
import pandas as pd


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




