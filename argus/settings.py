
import os

# set up paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# saved tables
TABLE_DIR = os.path.join(DATA_DIR, 'tables')

# database info
DATABASE_PATH = os.path.join(DATA_DIR, 'argus.db')
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'


API = 'http://argus-public.deltares.nl/db/table'


AVAILABLE_TABLES = [
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
]


FIELD_MAPPING = {
    'site': {
        'pk': 'seq',
        'id': 'id',
        'name': 'name',
        'timezone': 'TZName',
        'timezone_offset': 'TZoffset',
        'epsg': 'coordinateEPSG',
        'coordinate_rotation': 'coordinateRotation',
        'deg_from_north': 'degFromN',
        'lat': 'lat',
        'lon': 'lon',
        'elev': 'elev'
    },

    'station': {
        'pk': 'seq',
        'id': 'id',
        'site_id': 'siteID',
        'name': 'name',
        'short_name': 'shortName',
        'time_start': 'timeIN',
        'time_end': 'timeOUT'
    },

    'camera' : {
        'pk': 'seq',
        'id': 'id',
        'station_id': 'stationID',
        'intrinsic_parameters_id': 'IPID',
        'number': 'cameraNumber',
        'coord_x': 'x',
        'coord_y': 'y',
        'coord_z': 'z',
        'time_start': 'timeIN',
        'time_end': 'timeOUT',
    },

    'geometry': {
        'id': 'seq',
        'time_valid': 'whenValid',
        'camera_id': 'cameraID'
    },

    'gcp': {
        'pk': 'seq',
        'id': 'id',
        'site_id': 'siteID',
        'name': 'name',
        'coord_x': 'x',
        'coord_y': 'y',
        'coord_z': 'z',
        'time_start': 'timeIN',
        'time_end': 'timeOUT'
        },

    'usedGCP': {
        'pk': 'seq',
        'image_coord_horizontal': 'U',
        'image_coord_vertical': 'V',
        'gcp_id': 'gcpID',
        'geometry_id': 'geometrySequence'
        },

    'IP': {
        'pk': 'seq',
        'id': 'id',
        'name': 'name',
        'horizontal_pixels': 'width',
        'vertical_pixels': 'height'
        }
}


LOCAL_TABLES = list(FIELD_MAPPING.keys())


TABLE_MAPPING = {
    'usedGCP': 'used_gcp',
    'IP': 'intrinsic_parameters'
}


# for images ....
IMAGE_CATALOG_URL = "http://argus-public.deltares.nl/catalog"

IMAGE_BASE_URL = "http://argus-public.deltares.nl/sites"

IMAGE_BASIC_TYPES = ['snap', 'timex', 'min', 'max', 'var']

IMAGE_SITES = {
    'zandmotor': {
        'cameras': list(range(1, 13))
    }
}
