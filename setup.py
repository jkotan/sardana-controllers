#!/usr/bin/env python

# import os
# import imp
from setuptools import setup
from datetime import datetime

release = datetime.today().strftime('%Y.%m.%d.%H.%M').replace(".0", ".")

package_dir = {"sardana.PoolController": "python"}

packages = ["sardana.PoolController"]

provides =    ['python']


setup(name='PoolController',
      version=release,
      author="Sardana Controller Developers",
      author_email="fs-ec@desy.de",
      maintainer="DESY",
      maintainer_email="fs-ec@desy.de",
      url="https://github.com/desy-fsec/sardana-controllers/",
      packages=packages,
      package_dir=package_dir,
      include_package_data=True,
      provides=provides,
      )
