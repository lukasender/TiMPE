# -*- coding: utf-8; -*-
import os
import re
import ConfigParser
from setuptools import setup, find_packages

VERSIONFILE = open("src/timpe/app/__init__.py").read()
VERSION_REGEX = r'^__version__ = [\'"]([^\'"]*)[\'"]$'
M = re.search(VERSION_REGEX, VERSIONFILE, re.M)
if M:
    VERSION = M.group(1)
else:
    raise RuntimeError('Unable to find version string')


def get_versions():
    """picks the versions from version.cfg and returns them as dict"""
    versions_cfg = os.path.join(os.path.dirname(__file__), 'versions.cfg')
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    config.readfp(open(versions_cfg))
    return dict(config.items('versions'))


def nailed_requires(requirements):
    """returns the requirements list with nailed versions"""
    versions = get_versions()
    res = []
    for req in requirements:
        if '[' in req:
            name = req.split('[', 1)[0]
        else:
            name = req
        if name in versions:
            res.append('%s==%s' % (req, versions[name]))
        else:
            res.append(req)
    return res


def read(path):
    """ read a file """
    return open(os.path.join(os.path.dirname(__file__), path)).read()


HERE = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(HERE, 'README.md')).read()
CHANGES = open(os.path.join(HERE, 'CHANGES.txt')).read()

REQUIRES = [
    'crate [sqlalchemy]',
    'crash',
    'gevent',
    'lovely.pyrest',
    'pyramid',
    'pyramid_mailer',
    'requests',
    'urllib3',
    'zope.sqlalchemy',
]

TEST_REQUIRES = REQUIRES + [
    'lovely.testlayers',
    'mock>=1.0.1',
    'zope.testing',
    'webtest',
    'zc.customdoctests>=1.0.1'
]

setup(name='timpe',
      version=VERSION,
      description='A User to User Transaction System in a Shared-Nothing Environment',
      long_description='A ',
      classifiers=[
          "Programming Language :: Python",
      ],
      author='Lukas Ender',
      author_email='hello@lukasender.at',
      url='https://github.com/lumannnn/Transactions-in-Massively-Parallel-Environments',
      keywords='timpe user to user transactions shared-nothing',
      license='apache license 2.0',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['timpe'],
      include_package_data=True,
      extras_require=dict(
        test=nailed_requires([
          'lovely.testlayers',
          'mock>=1.0.1',
          'zope.testing',
          'webtest',
          'zc.customdoctests>=1.0.1'
        ]),
      ),
      zip_safe=False,
      install_requires=REQUIRES,
      tests_require=TEST_REQUIRES,
      test_suite="",
      entry_points={
          'paste.app_factory': [
              'main=timpe.app.server:app_factory'
          ],
          'paste.server_factory': [
              'server=timpe.app.green:server_factory',
          ],
          'console_scripts': [
              'app=pyramid.scripts.pserve:main',
          ],
      },
      )
