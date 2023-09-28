import os
from datetime import datetime


def common_exception_handler(exception, message):
    file_name = f'error_({datetime.now()}).txt'
    file_path = os.path.join('errors', file_name)
    with open(file_path, 'w') as error_file:
        error_file.write(f"{message}\n{exception}")
