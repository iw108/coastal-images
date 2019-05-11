
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

    'usedgcp': {
        'pk': 'seq',
        'image_coord_horizontal': 'U',
        'image_coord_vertical': 'V',
        'gcp_id': 'gcpID',
        'geometry_id': 'geometrySequence'
        },

    'ip': {
        'pk': 'seq',
        'id': 'id',
        'name': 'name',
        'horizontal_pixels': 'width',
        'vertical_pixels': 'height'
        }
}


TABLE_MAPPING = {
    'usedgcp': 'used_gcp',
    'ip': 'intrinsic_parameters'
}


def add_fields_site(entry):
    entry['epsg'] = (4826 if not entry['coordinateEPSG']
                     else entry['coordinateEPSG'])
    if entry['coordinateOrigin']:
       entry['lat'], entry['lon'], entry['elev'] = entry['coordinateOrigin'][0]
    return entry


def add_fields_camera(entry):
    if entry['K']:
        try:
            entry.update(
                focal_point_horizontal=abs(entry['K'][0][0]),
                focal_point_vertical=abs(entry['K'][1][1]),
                principal_point_horizontal=abs(entry['K'][2][0]),
                principal_point_vertical=abs(entry['K'][2][1]),
                skewness=abs(entry['K'][1][0])
            )
        except IndexError:
            pass

    if entry['Drad']:
        k1, k2, k3, k4 = entry['Drad'][0]
        entry.update(
            radial_dist_coef_first=k1, radial_dist_coef_second=k2,
            radial_dist_coef_third=k3, radial_dist_coef_fourth=k4
        )
    return entry


def post_process_usedgcp(table):
    all_pks = list(map(lambda item: item['pk'], table))
    max_pk = max(all_pks)
    duplicate_pks = set(pk for pk in all_pks if all_pks.count(pk) > 1)

    for duplicate_pk in duplicate_pks:
        duplicate_entries = [
            (index, item) for index, item in enumerate(table) if item['pk'] == duplicate_pk
        ]
        for index, item in duplicate_entries[1:]:
            max_pk += 1
            table[index]['pk'] = max_pk
    return table
