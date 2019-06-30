
from datetime import datetime
import json
import os
from re import sub as re_sub
import requests

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from . import utils


API = 'http://argus-public.deltares.nl/db/table'

AVAILABLE_TABLES = (
    "eurowave",
    "eurodata",
    "sequence",
    "usedGCP",
    "site",
    "keywords",
    "station",
    "lensModel",
    "cameraModel",
    "gcp",
    "camera",
    "template",
    "baseUsedGCP",
    "eurointertidal",
    "euromet",
    "IP",
    "eurotide",
    "baseGeometry",
    "geometry",
    "eurofielddata",
)


# set up paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')


# database info
DATABASE_PATH = os.path.join(DATA_DIR, 'argus.db')
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# saved tables
TABLE_DIR = os.path.join(DATA_DIR, 'tables')
LOCAL_TABLES = tuple(utils.FIELD_MAPPING.keys())


def get_table(table_name):
    """ get table from api """

    if table_name not in AVAILABLE_TABLES:
        raise ValueError("Table does not exist")
    return requests.get(('/').join((API, table_name))).json()


def extract_table(table_name):
    """ get table from api and save locally """

    table = get_table(table_name)
    file_path = os.path.join(TABLE_DIR, f"{table_name}.json")
    with open(file_path, 'w') as file:
        json.dump(table, file, indent=4)


def extract_all_tables():
    """ get all tables from the api and store locally """

    for table_name in AVAILABLE_TABLES:
        extract_table(table_name)


def list_local_tables():
    """ list all local tables """

    return {
        re_sub(r".json$", "", file): file for file in os.listdir(TABLE_DIR)
    }


def load_table(table_name):
    """ load a table stored locally """

    if not isinstance(table_name, str):
        raise TypeError
    table_name = table_name.lower()

    local_tables = list_local_tables()
    for local_name, file_name in local_tables.items():
        if table_name in (local_name.lower(), file_name.lower()):
            table_path = os.path.join(TABLE_DIR, file_name)
            with open(table_path, 'r') as file:
                table = json.load(file)
            return table
    print('Table does not exit')
    return None


def get_cleaned_table(table_name):
    """ load a table stored locally and process so it can be stored within
    model """

    table = load_table(table_name)
    if not table:
        return None

    table_name = re_sub(r".json$", "", table_name).lower()
    if table_name not in LOCAL_TABLES:
        print('Can not clean this table')
        return table

    columns = get_table_model(Base, table_name).__table__.columns.keys()

    key_mapping = utils.FIELD_MAPPING[table_name]
    hybrid_fields = getattr(
        utils, f'add_fields_{table_name}', lambda item: item
    )
    for entry in table:
        # add new fields and update key names
        entry = hybrid_fields(entry)
        entry.update({new: entry[old] for new, old in key_mapping.items()})

        # remove unwanted keys
        for key in set(entry.keys()) - set(columns):
            entry.pop(key)

        # convert timestamp fields to datetimes
        for key in filter(lambda column: column.startswith('time_'), columns):
            timestamp = entry[key]
            entry[key] = (datetime.utcfromtimestamp(timestamp)
                          if timestamp > 0 else None)

    post_process_table = getattr(
        utils, f'post_process_{table_name}', lambda item: item
    )
    return post_process_table(table)


def get_table_model(cls, table_name):

    if table_name in utils.TABLE_MAPPING.keys():
        table_name = utils.TABLE_MAPPING[table_name]

    for model_class in cls._decl_class_registry.values():
        if (hasattr(model_class, '__table__')
                and model_class.__table__.fullname == table_name):
            return model_class
    return None


def obj_to_dict(obj):
    output = obj.__dict__
    output.pop('_sa_instance_state')
    return output


def create_session():
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


def create_db(remove_existing=False):

    # check that the tables needed for db are avilable locally
    local_tables = {table.lower() for table in list_local_tables().keys()}
    if not all(table in local_tables for table in LOCAL_TABLES):
        raise ValueError('Extract all tables first')

    # remove existing database if it exists
    database_exists = os.path.exists(DATABASE_PATH)
    if database_exists and not remove_existing:
        print('Database already exists')
        return
    elif os.path.exists(DATABASE_PATH) and remove_existing:
        os.remove(DATABASE_PATH)

    all_entries = []
    for table_name in utils.FIELD_MAPPING.keys():
        table = get_cleaned_table(table_name)

        new_table_name = utils.TABLE_MAPPING.get(table_name, None)
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
    except Exception as e:
        print(e)
        session.rollback()
    finally:
        session.close()
