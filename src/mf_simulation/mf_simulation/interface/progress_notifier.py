import os

class ProgressNotifier():

    def __init__(self, log_file_path = "~/log_file"):

        self.__log_file_path = os.path.expanduser(log_file_path)

    def emit(self, msg: str):
        with open(self.__log_file_path, "a") as f:
            f.write(f"{msg}\n")