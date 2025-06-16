from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'forklift_controller'

from build_utils import setup_models

setup(
    name=package_name,
    version='0.0.0',
    #https://robotics.stackexchange.com/questions/97841/including-a-python-module-in-a-ros2-package
    packages=find_packages(exclude=['test']),
    data_files=[
        # First is destination, the other source
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/urdf', glob('urdf/*')),
        ('share/' + package_name + '/launch', glob('launch/forklift_launches/*')),
	    ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/worlds', glob('worlds/*.*')),
        ('share/'+package_name+'/config', glob('config/*')),
        ('share/' + package_name + '/maps/', glob('maps/*')),
        (('lib/' + package_name, ['forklift_controller/utils.py'])),
        (('lib/' + package_name, ['forklift_controller/MqttPayload.py'])),
        # How to get the directory where the executing script is
        # https://stackoverflow.com/questions/4934806/how-can-i-find-scripts-directory
        *setup_models(package_name, os.path.dirname(os.path.realpath(__file__)))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Elmeri Pohjois-Koivisto',
    maintainer_email='elmeri.pohjois-koivisto@tuni.fi',
    description='TODO: Package description',
    license='MIT License',
    #tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fork_node = forklift_controller.fork_node:main',
            'primitive_node = forklift_controller.primitive_node:main',
            'drone_controller = forklift_controller.drone_controller:main'
        ],
    },
)
