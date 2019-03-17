
import numpy as np

from sqlalchemy import select, func, create_engine, Column, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, column_property

from .settings import FRAME_DIMENSIONS


Base = declarative_base()


class Site(Base):

    __tablename__ = 'site'

    pk = Column(Integer, primary_key=True)
    id = Column(String(10))
    name = Column(String(10))
    timezone = Column(String(5))
    timezone_offset = Column(Integer)
    epsg = Column(Integer)
    lat = Column(Float)
    lon = Column(Float)
    elev = Column(Float)
    deg_from_north = Column(Float)
    coordinate_rotation = Column(Float)

    def __repr__(self):
        return f"<Site {self.name}>"

    @hybrid_property
    def origin_as_array(self):
        return np.array([self.lat, self.lon, self.elev])


class Station(Base):

    __tablename__ = 'station'

    pk = Column(Integer, primary_key=True)
    id = Column(String(10))
    name = Column(String(50))
    short_name = Column(String(10))
    time_start = Column(DateTime)
    time_end = Column(DateTime)

    # relationships
    site_id = Column(String(10), ForeignKey('site.id'))
    site = relationship("Site")

    def __repr__(self):
        return f"<Station {self.name}>"


class Camera(Base):

    __tablename__ = 'camera'

    pk = Column(Integer, primary_key=True)
    id = Column(String(10))
    number = Column(Integer)
    principal_point_horizontal = Column(Float)
    principal_point_vertical = Column(Float)
    focal_point_horizontal = Column(Float)
    focal_point_vertical = Column(Float)
    skewness = Column(Float)
    radial_dist_coef_first = Column(Float)
    radial_dist_coef_second = Column(Float)
    radial_dist_coef_third = Column(Float)
    radial_dist_coef_fourth = Column(Float)
    coord_x  = Column(Float)
    coord_y  = Column(Float)
    coord_z  = Column(Float)
    time_start = Column(DateTime)
    time_end = Column(DateTime)

    # relationships
    station_id = Column(String(10), ForeignKey('station.id'))
    station = relationship("Station")
    geometry = relationship("Geometry", lazy='dynamic')

    def __repr__(self):
        return f"<Camera {self.id}>"

    @hybrid_property
    def position(self):
        return np.array([self.coord_x, self.coord_y, self.coord_z])

    @hybrid_property
    def dist_coefs_for_cv2(self):
        return np.array([
            self.radial_dist_coef_first, self.radial_dist_coef_second, 0, 0,
            self.radial_dist_coef_third, self.radial_dist_coef_fourth, 0, 0,
        ])

    @hybrid_property
    def camera_matrix(self):
        return np.array([
            [self.focal_point_horizontal, self.skewness, self.principal_point_horizontal],
            [0, self.focal_point_vertical, self.principal_point_vertical],
            [0, 0, 1]
        ])

    @property
    def expected_frame_size(self):
        approx_frame_dims = [
            2 * self.focal_point_horizontal, 2 * self.focal_point_vertical
        ]

        expected_index = ((np.asarray(FRAME_DIMENSIONS) - approx_frame_dims)**2)\
                          .sum(axis=1).argmin()
        return tuple(FRAME_DIMENSIONS[expected_index])


class Gcp(Base):

    __tablename__ = 'gcp'

    pk = Column(Integer, primary_key=True)
    id = Column(String(10))
    name = Column(String(128))
    coord_x  = Column(Float)
    coord_y  = Column(Float)
    coord_z  = Column(Float)
    time_start = Column(DateTime)
    time_end = Column(DateTime)

    #relationships
    site_id = Column(String(10), ForeignKey('site.id'))

    @hybrid_property
    def object_points(self):
        return (self.coord_x, self.coord_y, self.coord_z)

    def __repr__(self):
        return f"<GCP {self.id}>"


class UsedGcp(Base):

    __tablename__ = 'used_gcp'

    pk = Column(Integer, primary_key=True)
    image_coord_horizontal = Column(Float)
    image_coord_vertical = Column(Float)

    #relationships
    geometry_id = Column(Integer, ForeignKey('geometry.id'))
    gcp_id = Column(String(10), ForeignKey('gcp.id'))

    @hybrid_property
    def image_points(self):
        return (self.image_coord_horizontal, self.image_coord_vertical)

    def __repr__(self):
        return f"<Used GCP {self.gcp_id}>"


class Geometry(Base):

    __tablename__ = 'geometry'

    id = Column(Integer, primary_key=True)
    time_valid = Column(DateTime)

    # relationships
    camera_id = Column(String(10), ForeignKey('camera.id'))

    gcp_count = column_property(
        select([func.count(UsedGcp.pk)]).\
            where(UsedGcp.geometry_id==id)
        )

    def __repr__(self):
        return f"<Geometry {self.camera_id}: {self.time_valid.strftime('%Y-%m-%d %H:%M')}>"
