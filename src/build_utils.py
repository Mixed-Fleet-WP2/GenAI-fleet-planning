from glob import glob
import os
import sys

def setup_models(package_name, curr_dir:str="models", data_tuples=None):

    # If we were to define the default as data_tuples=[]
    # and modified it inside the function, it would
    # modify the default value itself! See:
    # https://florimond.dev/en/posts/2018/08/python-mutable-defaults-are-the-source-of-all-evil
    if data_tuples == None:
        data_tuples = []

    try:
        children_files = [f for f in glob(f'{curr_dir}/*') if os.path.isfile(f)]

        # Install the files to the current path (if the directory contains them):
        if children_files:
            #print("File copied")
            data_tuples.append((f'share/{package_name}/{curr_dir}', children_files))

        # Recursively do the same for the children directories
        # because setup tools cannot copy directories
        # ! curr_dir prefix remains !
        children_dirs = [f for f in glob(f'{curr_dir}/*') if os.path.isdir(f)]
        
        for dir_path in children_dirs:
            setup_models(dir_path, data_tuples)
        return data_tuples
    except Exception as e:
        print(e, file=sys.stderr, flush=True)