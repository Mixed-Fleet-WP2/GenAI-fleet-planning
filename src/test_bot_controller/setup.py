from setuptools import find_packages, setup
from glob import glob

package_name = 'test_bot_controller'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        #Eka on destination, toinen on source
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/urdf', glob('urdf/*')),
        ('share/' + package_name + '/launch', ['launch/joint_launch.py']),
        ('share/' + package_name + '/launch', ['launch/test_launch.py']),
        ('share/' + package_name + '/worlds', ['worlds/empty.world']),
        ('share/'+package_name+'/config', ['config/ros_gz_bridge.yaml']),
        ('share/' + package_name + '/meshes/', glob('meshes/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='elmeripk',
    maintainer_email='elmeripk@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fork_node = test_bot_controller.fork_node:main',
            'rotation_node = test_bot_controller.rotation_node:main'
        ],
    },
)
