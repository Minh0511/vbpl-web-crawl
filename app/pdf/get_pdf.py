import os
import re
import urllib.parse
import requests


def get_pdf(pdf_url, folder_path):
    os.makedirs(folder_path, exist_ok=True)

    file_name_from_url = os.path.basename(pdf_url)
    decoded_file_name = urllib.parse.unquote_plus(file_name_from_url)

    match = re.search(r'/Attachments/(\d+)/', pdf_url)
    if match:
        file_id = match.group(1)
    else:
        file_id = "noId"

    file_name = f"({file_id})-{decoded_file_name}"
    file_path = os.path.join(folder_path, file_name)

    response = requests.get(pdf_url)
    if response.status_code == 200:
        with open(file_path, 'wb') as pdf_file:
            pdf_file.write(response.content)
    else:
        print(f"Failed to download PDF")

    response.close()
