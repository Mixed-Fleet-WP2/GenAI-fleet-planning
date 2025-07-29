import os
import sys


#https://stackoverflow.com/questions/141291/how-to-list-only-top-level-directories-in-python

# Path prefix: absolute path to the parent folder of curr_dir
def setup_models(package_name, path_prefix, curr_dir:str="models", data_tuples=None):

    # If we were to define the default as data_tuples=[]
    # and modified it inside the function, it would
    # modify the default value itself! See:
    # https://florimond.dev/en/posts/2018/08/python-mutable-defaults-are-the-source-of-all-evil
    if data_tuples == None:
        data_tuples = []

    source_path = os.path.join(path_prefix, curr_dir)

    try:
        # Get files inside the folder (without any path prefixes, just plain names)
        # and add the current dir as prefix
        children_files = [os.path.join(curr_dir, f) for f in os.listdir(source_path) if os.path.isfile(os.path.join(source_path, f))]

        # Install the files to the current path (if the directory contains them):
        if children_files:
            data_tuples.append((f'share/{package_name}/{curr_dir}', children_files))

        # Recursively do the same for the children directories
        # because setup tools cannot copy directories
        
        # Get folders inside the folder (without any path prefixes, just plain names)
        # and add the current dir as prefix
        children_dirs = [os.path.join(curr_dir, f) for f in os.listdir(source_path) if os.path.isdir(os.path.join(source_path, f))]
        for dir_path in children_dirs:
            
            setup_models(package_name, path_prefix, dir_path, data_tuples)
        #print(data_tuples, file=sys.stderr, flush=True)
        return data_tuples
    except Exception as e:
        print(e, file=sys.stderr, flush=True)