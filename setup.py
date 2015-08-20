# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os

version = '0.0.1'

setup(
    name='propshikari',
    version=version,
    description='Application for hunterscamp and rest management',
    author='New Indictrans',
    author_email='contact@indictranstech.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=("frappe",),
)
