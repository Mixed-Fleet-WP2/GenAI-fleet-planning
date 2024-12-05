from setuptools import find_packages, setup
from glob import glob

package_name = 'forklift_controller'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        #Eka on destination, toinen on source
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/urdf', glob('urdf/*')),
        ('share/' + package_name + '/turtle_urdf', glob('turtle_urdf/*')),
        ('share/' + package_name + '/launch', ['launch/joint_launch.py']),
        ('share/' + package_name + '/launch', ['launch/navigate_to_point_launch.py']),
        ('share/' + package_name + '/launch', ['launch/test_launch.py']),
        ('share/' + package_name + '/launch', ['launch/turtle_launch.py']),
        ('share/' + package_name + '/launch', ['launch/rviz_launch.py']),
        ('share/' + package_name + '/launch', ['launch/spawn_tb4.launch.py']),
        ('share/' + package_name + '/launch', ['launch/forklift_launch.py']),
        ('share/' + package_name + '/launch', ['launch/forklift_slam.py']),
        ('share/' + package_name + '/worlds', ['worlds/empty.world']),
        ('share/' + package_name + '/worlds', ['worlds/depot.sdf']),
        ('share/'+package_name+'/config', ['config/ros_gz_bridge.yaml']),
        ('share/'+package_name+'/config', ['config/config.rviz']),
        ('share/'+package_name+'/config', ['config/tb4_bridge.yaml']),
        ('share/' + package_name + '/meshes/', glob('meshes/*')),
        #In the future, move the forklift.py to the lib directory?
        (('share/' + package_name + '/gui', ['forklift_controller/control.py'])),
        (('share/' + package_name + '/gui', ['forklift_controller/forklift.py'])),
        (('lib/' + package_name, ['forklift_controller/utils.py'])),
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
            'fork_node = forklift_controller.fork_node:main',
            'primitive_node = forklift_controller.primitive_node:main',
            'nav_node = forklift_controller.navigate:main',
        ],
    },
)
