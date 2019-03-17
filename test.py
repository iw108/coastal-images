
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, join

from argus.core import obj_to_dict, create_session
from argus.models import Camera, Geometry, UsedGcp, Gcp
from argus.camera import Camera as CameraClass


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


# get coords
id = int((df['time_valid'] - time_start).abs().idxmin())

used_gcps = session.query(UsedGcp, Gcp).join(Gcp)\
            .filter(UsedGcp.geometry_id==id).all()

image_points, object_points = [], []
for used_gcp, gcp in used_gcps:
    image_points.append(used_gcp.image_points)
    object_points.append(gcp.object_points)


camera = CameraClass(camera.camera_matrix, camera.dist_coefs_for_cv2,
                   camera.expected_frame_size)

camera.rectify(np.asarray(object_points), np.asarray(image_points))



session.close()
