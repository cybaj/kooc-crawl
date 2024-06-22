from setuptools import find_packages, setup

setup(
    name='kooc-crawler',
    packages=find_packages(),
    version="0.0.1",
    install_requires=[
       'beautifulsoup4',
       'selenium',
       'selenium-wire',
       'm3u8',
    ]
)
