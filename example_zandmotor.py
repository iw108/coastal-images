
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

from argus.core import create_session
from argus.models import Site
from argus.projections import Rotation

from zandmotor.topo import GPS
from zandmotor.meteo import get_meteo, average_angles


time_start = datetime(2014, 1, 1)
time_end = datetime(2014, 1, 2)


# load some argus site and init rotation class
session = create_session()
site = session.query(Site).filter_by(id='ZMXXXXX').first()
session.close()

rotation = Rotation(site.lat, site.lon, site.coordinate_rotation)


# load a gps survey and interpolate
gps_class = GPS()

lon, lat, elev = gps_class.interpolate_data(
    *gps_class.load_topo_from_datetime(time_start)[:-1]
)

# rotate topo survey to argus coordinate system as present
lon_grid, lat_grid = np.meshgrid(lon, lat)
coords = rotation.local_to_argus(
    np.column_stack((lon_grid.flatten(), lat_grid.flatten()))
)
x_grid = coords[:, 0].reshape(lat_grid.shape)
y_grid = coords[:, 1].reshape(lon_grid.shape)


plt.figure()
plt.pcolormesh(y_grid, x_grid, elev)


# check that we can access the meteo data
df_meteo = get_meteo(time_start, time_end, variables=('WindDir_Avg',))

# resample
df_resampled = df_meteo.resample('1H', label='right', closed='right')\
           .agg(average_angles)

plt.figure()
plt.plot(df_meteo, 'k', alpha=0.3)
plt.plot(df_resampled, '-ok', markersize=3)
plt.ylim(0, 360)
