from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'mf_simulation'

def setup_models():
    #https://stackoverflow.com/questions/141291/how-to-list-only-top-level-directories-in-python
    #Get the top-level model directories
    model_dirnames = next(os.walk('./models'))[1]
    model_dirname_paths = [f"models/{model_dir}" for model_dir in model_dirnames]
    
    # Retrieve the files from directory (.config and .sdf)
    for model_path in model_dirname_paths:
        children_files = [f for f in glob(f'{model_path}/*', recursive=True) if os.path.isfile(f)]
        nested_dirs = next(os.walk(model_path))[1]
        print(nested_dirs)

    #TODO: COPY MESHES
 

setup_models()

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
        (f"share")
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
