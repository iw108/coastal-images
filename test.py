from argus.core import *
from argus import models


print(load_table('station'))

print(load_table('station'))

# stations = get_table('station')
# print(process_station(stations[-1]))


# cameras = get_table('camera')
# print(process_camera(cameras[-1]))

# gcps = get_table('gcp')
# gcp = process_gcp(gcps[-1])
# print(models.Gcp(**gcp).time_start)

# geometries = get_table('geometry')
# geometry = process_geometry(geometries[-1])
# print(models.Geometry(**geometry))

# gcps = argus.get_table('usedGCP')
# print(utils.process_used_gcp(gcps[-1]))
