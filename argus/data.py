
import requests

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
    "euromorph",
    "gcp",
    "camera",
    "template",
    "baseUsedGCP",
    "eurointertidal",
    "euromet",
    "IP",
    "UTM",
    "dbdefs",
    "eurotide",
    "baseGeometry",
    "geometry",
    "eurofielddata",
]


class Argus(object):

    api = 'http://argus-public.deltares.nl/db/table'
    tables = AVAILABLE_TABLES

    def get_table(self, table_name):
        if table_name not in self.tables:
            raise ValueError("Table does not exist")
        return requests.get(('/').join((self.api, table_name))).json()


def process_site(site):
    key_mapping = {
        'pk': 'seq',
        'id': 'id',
        'name': 'name',
        'timezone': 'TZName',
        'timezone_offset': 'TZoffset',
        'epsg': 'coordinateEPSG',
        'coordinate_rotation': 'coordinateRotation',
        'deg_from_north': 'degFromN',
        'timestamp': 'timestamp',
        'lat': 'lat',
        'lon': 'lon',
        'elev': 'elev'
    }

    store = {new_key: site[old_key] for new_key, old_key in key_mapping.items()}

    store['epsg'] = 4826 if not store['epsg'] else store['epsg']
    if site['coordinateOrigin']:
       store['lat'], store['lon'], store['elev'] = site['coordinateOrigin'][0]
    return store


def process_station(station):
    key_mapping = {
        'pk': 'seq',
        'id': 'id',
        'site_id': 'siteID',
        'name': 'name',
        'short_name': 'shortName',
        'time_start': 'timeIN',
        'time_end': 'timeOUT'
    }
    store = {new_key: station[old_key] for new_key, old_key in key_mapping.items()}
    return store


def process_camera(camera):
    key_mapping = {
        'pk': 'seq',
        'id': 'id',
        'station_id': 'stationID',
        'number': 'cameraNumber',
        'coord_x': 'x',
        'coord_y': 'y',
        'coord_z': 'z'
    }
    store = {new_key: camera[old_key] for new_key, old_key in key_mapping.items()}

   if camera['K']:
       try:
            camera_matrix = {
                'focal_point_horizontal': abs(cam['K'][0][0]),
                'focal_point_vertical': abs(cam['K'][1][1]),
                'principal_point_horizontal': abs(cam['K'][2][0]),
                'principal_point_vertical': abs(cam['K'][2][1]),
                'skewness': abs(cam['K'][1][0])
            }
            store.update(camera_matrix)
        except IndexError:
            print('No camera matrix')

    if camera['Drad']
        k1, k2, k3, k4 = cam['Drad'][0]
        store.update(radial_dist_coef_first=k1, radial_dist_coef_second=k2,
                     radial_dist_coef_third=k3, radial_dist_coef_fourth=k4)

    return store
