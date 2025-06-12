from setuptools import find_packages, setup
from glob import glob
import sys
import os
package_name = 'mf_simulation'

# Add the build_utils.py to path
# https://stackoverflow.com/questions/3108285/in-python-script-how-do-i-set-pythonpath
#sys.path.append(os.path.abspath('../'))

#print(sys.path, file=sys.stderr, flush=True)
from build_utils import setup_models

# Get directory of this file
#https://stackoverflow.com/questions/4934806/how-can-i-find-scripts-directory

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*')),
        (f'share/{package_name}/config', glob('config/*')),
        (f'share/{package_name}/maps', glob('maps/*')),
        (f'share/{package_name}/worlds', glob('worlds/*')),
        *setup_models(package_name, os.path.dirname(os.path.realpath(__file__)))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='elmeripk',
    maintainer_email='elmeripeekoo@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
