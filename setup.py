
from setuptools import setup

setup(
   name='coastal-images',
   version='0.1',
   description='packages for argus images',
   author='Isaac Williams',
   author_email='isaac.williams.devel@gmail.com',
   include_package_data=True,
   packages=['argus', 'zandmotor'],  #same as name
   install_requires=[
       'pandas',
       'numpy',
       'netCDF4<1.4',
       'SQLAlchemy',
       'opencv-contrib-python',
       'pytz',
       'ephem',
       'pyproj',
       'requests',
       'scipy',
       ], #external packages as dependencies
)
