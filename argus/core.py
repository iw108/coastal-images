
from datetime import datetime
import json
import os
import re
import requests

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .settings import API, AVAILABLE_TABLES, TABLE_DIR, FIELD_MAPPING, DATABASE_PATH


def get_table(table_name):
    if table_name not in AVAILABLE_TABLES:
        raise ValueError("Table does not exist")
    return requests.get(('/').join((API, table_name))).json()


def clean_site(site):
    key_mapping = FIELD_MAPPING['site']
    store = {new_key: site[old_key] for new_key, old_key in key_mapping.items()}
    store['epsg'] = 4826 if not store['epsg'] else store['epsg']
    if site['coordinateOrigin']:
       store['lat'], store['lon'], store['elev'] = site['coordinateOrigin'][0]
    return store


def clean_station(station):
    key_mapping = FIELD_MAPPING['station']
    store = {new_key: station[old_key] for new_key, old_key in key_mapping.items()}
    store['time_start'] = datetime.utcfromtimestamp(store['time_start'])
    store['time_end'] = datetime.utcfromtimestamp(store['time_end']) if store['time_end'] else None
    return store


def clean_camera(camera):
    key_mapping = FIELD_MAPPING['camera']
    store = {new_key: camera[old_key] for new_key, old_key in key_mapping.items()}

    if camera['K']:
        try:
            camera_matrix = {
                'focal_point_horizontal': abs(camera['K'][0][0]),
                'focal_point_vertical': abs(camera['K'][1][1]),
                'principal_point_horizontal': abs(camera['K'][2][0]),
                'principal_point_vertical': abs(camera['K'][2][1]),
                'skewness': abs(camera['K'][1][0])
            }
            store.update(camera_matrix)
        except IndexError:
            print('No camera matrix')

    if camera['Drad']:
        k1, k2, k3, k4 = camera['Drad'][0]
        store.update(radial_dist_coef_first=k1, radial_dist_coef_second=k2,
                     radial_dist_coef_third=k3, radial_dist_coef_fourth=k4)

    store['time_start'] = datetime.utcfromtimestamp(store['time_start'])
    store['time_end'] = datetime.utcfromtimestamp(store['time_end']) if store['time_end'] else None

    return store

def clean_geometry(geometry):
    key_mapping = FIELD_MAPPING['geometry']
    store = {new_key: geometry[old_key] for new_key, old_key in key_mapping.items()}
    store['time_valid'] = datetime.utcfromtimestamp(store['time_valid'])
    return store


def clean_gcp(gcp):
    key_mapping = FIELD_MAPPING['gcp']
    store = {new_key: gcp[old_key] for new_key, old_key in key_mapping.items()}

    store['time_start'] = datetime.utcfromtimestamp(store['time_start'])
    store['time_end'] = datetime.utcfromtimestamp(store['time_end']) if store['time_end'] else None
    return store


def clean_used_gcp(used_gcp):
    key_mapping = FIELD_MAPPING['usedGCP']
    store = {new_key: used_gcp[old_key] for new_key, old_key in key_mapping.items()}
    return store


def get_table_function(table_name):

    clean_functions = [
        clean_site,
        clean_station,
        clean_camera,
        clean_geometry,
        clean_gcp,
        clean_used_gcp
    ]

    for function in clean_functions:
        name = function.__name__
        processed_name = re.sub(r"^process", "", name.replace('_', ''))
        if processed_name.lower() == table_name.lower():
            return function
    return None


def load_table(table_name, process=True):

    expected_path = os.path.join(TABLE_DIR, f"{table_name}.json")
    if os.path.exists(expected_path):
        with open(expected_path, 'r') as file:
            table = json.load(file)

        clean_function = get_table_function(table_name)
        if process and callable(clean_function):
            table = [clean_function(item) for item in table]
        return table
    return None


def extract_data():

    save_table = [False for i in range(len(AVAILABLE_TABLES))]
    for index, table_name in enumerate(AVAILABLE_TABLES):
        try:
            table = get_table(table_name)
            save_table[index] = True
        except Exception as e:
            print('Could not get table')
            pass

        if save_table[index] == True:
            with open(os.path.join(DATA_DIR, 'tables', f"{table_name}.json"), 'w') as file:
                json.dump(table, file, indent=4)
