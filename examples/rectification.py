
from datetime import datetime, timedelta

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from argus.core import obj_to_dict, create_session
from argus.models import Camera, Geometry, UsedGcp, Gcp
from argus.camera import Camera as ArgusCamera
from argus.images import IMAGE_BASE_URL, get_images, load_image


session = create_session()

camera_id = 'ZMXX01C'
time_start = datetime(2013, 11, 1)


# query camera model to get the specfied camera
camera = session.query(Camera).filter_by(id=camera_id).first()
ZMXX01C = ArgusCamera(camera.camera_matrix, camera.dist_coefs_for_cv2,
                      camera.intrinsic_parameters.frame_size)


# get camera geometries and store in dataframe
geometries = camera.geometry.filter(Geometry.gcp_count > 5)\
             .order_by(Geometry.time_valid).all()

df = pd.DataFrame([obj_to_dict(geom) for geom in geometries])\
     .set_index('id').drop(columns=['camera_id'])


# get closest camera geometry and get the image and object points of used gcps
id = int((df['time_valid'] - time_start).abs().idxmin())

used_gcps = session.query(UsedGcp, Gcp).join(Gcp)\
            .filter(UsedGcp.geometry_id == id).all()
session.close()


# process the used used gcps.
distorted_image_points, object_points = [], []
for used_gcp, gcp in used_gcps:
    distorted_image_points.append(used_gcp.image_points)
    object_points.append(gcp.object_points)

# convert the above lists into arrays and undistort the image points
distorted_image_points, object_points = map(
    lambda item: np.asarray(item), (distorted_image_points, object_points)
)
undistorted_image_points = ZMXX01C.undistort_points(distorted_image_points)


# now we can recitfy camera. Calculate the expected position of object points
ZMXX01C.rectify(object_points, undistorted_image_points)
calculated_image_points = ZMXX01C.object_to_image_points(object_points)


# in order to present everything get an image from the desired camera, and plot
# the calculated and known image points

# get a dataframe with image urls for selected camera
df_images = get_images(
    time_start=time_start, time_end=time_start + timedelta(days=1),
    cameras=camera.number, image_types='snap'
)

# contruct full url and load image
image_url = IMAGE_BASE_URL + df_images.snap[5]
print(image_url)
image = load_image(image_url)

# plot the results
plt.figure()
plt.imshow(ZMXX01C.undistort_image(image))
plt.plot(*undistorted_image_points.T, 'or')
plt.plot(*calculated_image_points.T, 'ok')
