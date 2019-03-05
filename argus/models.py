
import numpy as np

from sqlalchemy import create_engine, Column, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base


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
    timestamp = Column(Integer)

    def __repr__(self):
        return f"< Site {self.site_name}>"

    @property
    def origin_as_array(self):
        return np.array([lat, lon, elev])


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

    def __repr__(self):
        return f"< Station {self.name}>"


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

    # relationships
    station_id = Column(String(10), ForeignKey('station.id'))

    def __repr__(self):
        return f"< Camera {self.id}>"
