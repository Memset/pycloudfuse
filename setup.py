#!/usr/bin/env python
from setuptools import setup, find_packages

setup(name='pycloudfuse',
      version="0.02",
      description='Fuse (Filesystem in Userspace) interface to Rackspace Cloud Files and Open Stack Object Storage (Swift)',
      author='Nick Craig-Wood',
      author_email='nick@memset.com',
      url="https://github.com/memset/pycloudfuse",
      license='MIT',
      include_package_data=True,
      zip_safe=False,
      install_requires=['fuse-python', 'python-cloudfiles', 'ftp-cloudfs>=0.9'],
      scripts=['pycloudfuse'],
      #packages = find_packages(exclude=['tests', 'debian']),
      #tests_require = ["nose"],
      classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Programming Language :: Python',
        'Operating System :: Linux',
        'Environment :: No Input/Output (Daemon)',
        'License :: OSI Approved :: MIT License',
        ],
      #test_suite = "nose.collector",
      )
