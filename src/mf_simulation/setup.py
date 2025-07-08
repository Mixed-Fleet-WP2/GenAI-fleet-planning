#type: ignore
from setuptools import find_packages, setup
from glob import glob

import os
package_name = 'mf_simulation'

# https://stackoverflow.com/questions/3108285/in-python-script-how-do-i-set-pythonpath
from build_utils import setup_models
# Get directory of this file
#https://stackoverflow.com/questions/4934806/how-can-i-find-scripts-directory

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=["test"]),
    package_data={
        "mf_simulation.interface": ["*.qss", "templates/*.jinja", ".env", "*.yaml"],
    },
    # Surpress warnings about templates/ being treated as a package
    include_package_data=False,
    
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*')),
        (f'share/{package_name}/config', glob('config/*')),
        (f'share/{package_name}/maps', glob('maps/*')),
        (f'share/{package_name}/worlds', glob('worlds/*')),
        #(f'share/{package_name}/templates', glob('templates/*')),
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
            'interface = mf_simulation.interface.interface:main'
        ],
    },
)