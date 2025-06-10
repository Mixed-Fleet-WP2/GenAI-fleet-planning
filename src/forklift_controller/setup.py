from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'forklift_controller'

def define_models() -> list:
    """
    Utility function to define the models and their corresponding data files.
    Needed because glob doesnt copy directories.
    """
    model_names = os.listdir("./models")
    data_tuples = []

    for model_name in model_names:

        #Copy the meshes first
        destination = f'share/{package_name}/models/{model_name}/meshes/'
        source = f'models/{model_name}/meshes/*'

        # Copy the files from source to destination
        data_tuples.append((destination, glob(source)))

        #Copy materials if applicable (glob(materials_source) returns empty list if no materials)
        materials_source = f'models/{model_name}/materials/textures/*'
        materials_destination = f'share/{package_name}/models/{model_name}/materials/textures/'
        data_tuples.append((materials_destination, glob(materials_source)))

        #Move one level up to get the sdf files aka models/model_name

        sdf_folder_dest = os.path.dirname(os.path.dirname(destination))
        sdf_folder_src = os.path.dirname(os.path.dirname(source))
          
        #Copy the sdf and model.config files
        data_tuples.append((sdf_folder_dest, glob(f"{sdf_folder_src}/*.sdf")))
        data_tuples.append((sdf_folder_dest, glob(f"{sdf_folder_src}/model.config")))
        
    return data_tuples



setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        #Eka on destination, toinen on source
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/urdf', glob('urdf/*')),
        ('share/' + package_name + '/launch', glob('launch/forklift_launches/*')),
	    ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/worlds', glob('worlds/*.*')),
        ('share/'+package_name+'/config', glob('config/*')),
        ('share/' + package_name + '/maps/', glob('maps/*')),
        #In the future, move the forklift.py to the lib directory?
        (('share/' + package_name + '/gui', ['forklift_controller/GUI.py'])),
        (('share/' + package_name + '/gui', ['forklift_controller/sv.tcl'])),
        (('share/' + package_name + '/gui', ['forklift_controller/controller.py'])),
        (('share/' + package_name + '/gui', ['forklift_controller/robots.xml'])),
        (('lib/' + package_name, ['forklift_controller/utils.py'])),
        (('lib/' + package_name, ['forklift_controller/MqttPayload.py'])),
        *define_models()
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Elmeri Pohjois-Koivisto',
    maintainer_email='elmeri.pohjois-koivisto@tuni.fi',
    description='TODO: Package description',
    license='TODO: License declaration',
    #tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fork_node = forklift_controller.fork_node:main',
            'primitive_node = forklift_controller.primitive_node:main',
            'drone_controller = forklift_controller.drone_controller:main'
        ],
    },
)
