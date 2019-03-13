
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, join

from argus.core import obj_to_dict, create_session
from argus.models import Camera, Geometry, UsedGcp, Gcp


session = create_session()

camera_id = 'ZMXX01C'
time_start = datetime(2013, 11, 1)

# query camera model
camera = session.query(Camera).filter_by(id=camera_id).first()

# get camera geometries and store in dataframe
geometries = camera.geometry.filter(Geometry.gcp_count > 5)\
             .order_by(Geometry.time_valid).all()

df = pd.DataFrame([obj_to_dict(geom) for geom in geometries])\
     .set_index('id').drop(columns=['camera_id'])
df['time_elapsed'] = abs(df['time_valid'] - time_start)

# get coords
id = int(df['time_elapsed'].idxmin())

coords = session.query(UsedGcp, Gcp).join(Gcp)\
         .filter(UsedGcp.geometry_id==id).all()

session.close()
