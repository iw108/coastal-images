from argus.core import create_db
from argus import models, settings

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, subqueryload


engine = create_engine(settings.DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()


site_id = 'ZMXXXXX'
station_id = 'ZMXX00S'
camera_id = 'ZMXX01C'


# check that bi-directional relationships work

# query site model
site = session.query(models.Site).filter_by(id=site_id).first()
station = site.station.filter_by(id=station_id).first()
camera = station.camera.filter_by(id=camera_id).first()
print(site, station, camera)


# query station model
station = session.query(models.Station).filter_by(id=station_id).first()
camera = station.camera.filter_by(id=camera_id).first()
print(station.site, station, camera)


# query camera model
camera = session.query(models.Camera).filter_by(id=camera_id).first()
print(camera.station.site, camera.station, camera)

session.close()
