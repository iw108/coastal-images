
from datetime import datetime
import json
import os
import re
import requests

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .settings import *
from .models import Base


def get_table(table_name):
    if table_name not in AVAILABLE_TABLES:
        raise ValueError("Table does not exist")
    return requests.get(('/').join((API, table_name))).json()


class ProcessTables(object):

    @staticmethod
    def clean_site(site):
        key_mapping = FIELD_MAPPING['site']
        store = {new_key: site[old_key] for new_key, old_key in key_mapping.items()}
        store['epsg'] = 4826 if not store['epsg'] else store['epsg']
        if site['coordinateOrigin']:
           store['lat'], store['lon'], store['elev'] = site['coordinateOrigin'][0]
        return store

    @staticmethod
    def clean_station(station):
        key_mapping = FIELD_MAPPING['station']
        store = {new_key: station[old_key] for new_key, old_key in key_mapping.items()}
        store['time_start'] = datetime.utcfromtimestamp(store['time_start'])
        store['time_end'] = datetime.utcfromtimestamp(store['time_end']) if store['time_end'] else None
        return store

    @staticmethod
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
                pass

        if camera['Drad']:
            k1, k2, k3, k4 = camera['Drad'][0]
            store.update(radial_dist_coef_first=k1, radial_dist_coef_second=k2,
                         radial_dist_coef_third=k3, radial_dist_coef_fourth=k4)

        store['time_start'] = datetime.utcfromtimestamp(store['time_start'])
        store['time_end'] = datetime.utcfromtimestamp(store['time_end']) if store['time_end'] else None

        return store

    @staticmethod
    def clean_geometry(geometry):
        key_mapping = FIELD_MAPPING['geometry']
        store = {new_key: geometry[old_key] for new_key, old_key in key_mapping.items()}
        store['time_valid'] = datetime.utcfromtimestamp(store['time_valid'])
        return store

    @staticmethod
    def clean_gcp(gcp):
        key_mapping = FIELD_MAPPING['gcp']
        store = {new_key: gcp[old_key] for new_key, old_key in key_mapping.items()}

        store['time_start'] = datetime.utcfromtimestamp(store['time_start'])
        store['time_end'] = datetime.utcfromtimestamp(store['time_end']) if store['time_end'] else None
        return store

    @staticmethod
    def clean_usedgcp(used_gcp):
        key_mapping = FIELD_MAPPING['usedGCP']
        store = {new_key: used_gcp[old_key] for new_key, old_key in key_mapping.items()}
        return store

    @classmethod
    def get_clean_functions(cls):
        functions = {}
        for name, method in cls.__dict__.items():
            if name.startswith('clean'):
                functions.update({
                    re.sub(r"^clean", "", name.replace('_', '')).lower(): method
                })
        return functions

    @classmethod
    def clean_table(cls, table_name, table):
        functions = cls.get_clean_functions()
        if table_name.lower() not in functions.keys():
            return table
        return [functions[table_name.lower()].__func__(item) for item in table]


process_tables = ProcessTables()


def get_table_model(cls, table_name):
    for model_class in cls._decl_class_registry.values():
        if (hasattr(model_class, '__table__')
               and model_class.__table__.fullname == table_name):
            return model_class
    return None


def load_table(table_name, process=True):

    expected_path = os.path.join(TABLE_DIR, f"{table_name}.json")
    if os.path.exists(expected_path):
        with open(expected_path, 'r') as file:
            table = json.load(file)
        return process_tables.clean_table(table_name, table)
    return None


def extract_table(table_name):

    if not table_name in AVAILABLE_TABLES:
        return

    try:
        table = get_table(table_name)
        save_table = True
    except Exception as e:
        print('Could not get table')
        save_table = False
        pass

    if save_table:
        file_path = os.path.join(TABLE_DIR, f"{table_name}.json")
        with open(file_path, 'w') as file:
            json.dump(table, file, indent=4)


def get_local_tables():
    return [re.sub(r".json$", "", file).lower() for file in os.listdir(TABLE_DIR)]


def create_db():

    all_entries = []
    for table_name in LOCAL_TABLES:

        table = load_table(table_name)

        # work around to account for dupiclate primary keys
        if table_name == 'usedGCP':
            all_pks = list(map(lambda item: item['pk'], table))
            max_pk = max(all_pks)
            duplicate_pks = set([pk for pk in all_pks if all_pks.count(pk) > 1])

            for duplicate_pk in duplicate_pks:
                duplicate_entries = [
                    (index, item) for index, item in enumerate(table) if item['pk'] == duplicate_pk
                ]
                for index, item in duplicate_entries[1:]:
                    max_pk += 1
                    table[index]['pk'] = max_pk

        new_table_name = TABLE_MAPPING.get(table_name, None)
        table_name = new_table_name if new_table_name else table_name
        model = get_table_model(Base, table_name)

        all_entries += [model(**item) for item in table]

    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        session.add_all(all_entries)
        session.commit()
    except:
        session.rollback()
    finally:
        session.close()
