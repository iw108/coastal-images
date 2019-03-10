
import numpy as np

from sqlalchemy import create_engine, Column, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


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

    # relationships
    station = relationship("Station")

    def __repr__(self):
        return f"<Site {self.name}>"

    @property
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
    camera = relationship("Camera")

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
    geometry = relationship("Geometry")

    def __repr__(self):
        return f"<Camera {self.id}>"

    @property
    def position(self):
        return np.array([self.coord_x, self.coord_y, self.coord_z])

    @property
    def dist_coefs_for_cv2(self):
        return np.array([
            self.radial_dist_coef_first, self.radial_dist_coef_second,
            self.radial_dist_coef_third, self.radial_dist_coef_fourth
            ])

    @property
    def camera_matrix(self):
        return np.array([
            [self.focal_point_horizontal, self.skewness, self.principal_point_horizontal],
            [0, self.focal_point_vertical, self.principal_point_vertical],
            [0, 0, 1]
            ])


class Geometry(Base):

    __tablename__ = 'geometry'

    id = Column(Integer, primary_key=True)
    time_valid = Column(DateTime)

    # relationships
    camera_id = Column(String(10), ForeignKey('camera.id'))
    used_gcp = relationship('Used_gcp', cascade="all, delete-orphan")


    def __repr__(self):
        return f"<Geometry {self.camera_id}: {self.time_valid.strftime('%Y-%m-%d %H:%M')}>"


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

    def __repr__(self):
        return f"<GCP {self.id}>"


class Used_gcp(Base):

    __tablename__ = 'used_gcp'

    pk = Column(Integer, primary_key=True)
    image_coord_horizontal = Column(Float)
    image_coord_vertical = Column(Float)

    #relationships
    geometry_id = Column(Integer, ForeignKey('geometry.id'))
    gcp_id = Column(String(10), ForeignKey('gcp.id'))

    def __repr__(self):
        return f"<Used GCP {self.gcp_id}>"
