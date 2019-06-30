
from datetime import datetime

from netCDF4 import Dataset
from pytz import utc as pytz_utc


def timestamp_to_datetime(timestamp):
    return pytz_utc.localize(datetime.utcfromtimestamp(timestamp))


def parse_datetime(datetime_obj):

    if not isinstance(datetime_obj, datetime):
        raise TypeError

    if not datetime_obj.tzinfo:
        return pytz_utc.localize(datetime_obj)
    else:
        return datetime_obj.astimezone(pytz_utc)


def open_with_retries(file_path, retries=3):
    try:
        return Dataset(file_path, 'r')
    except OSError as exception:
        if retries > 0:
            print(f"Retrying {file_path}")
            return open_with_retries(file_path, retries=retries - 1)
        else:
            raise OSError(exception)
