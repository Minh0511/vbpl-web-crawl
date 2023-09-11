import os
import re
import urllib.parse
import requests
import requests.packages
import urllib3.exceptions
from bs4 import BeautifulSoup


def get_anle_file_name(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    content_disposition = response.headers.get('Content-Disposition')
    if content_disposition:
        match_file_name = re.search(r'filename=(.*?)(?:;|$)', content_disposition)
        if match_file_name:
            return match_file_name.group(1)
    else:
        # If content-disposition didn't provide the filename, try to extract from the HTML content
        title_tag = soup.title
        if title_tag:
            return title_tag.text

    return None


def get_pdf(pdf_url, folder_path, is_vbpl):
    try:
        os.makedirs(folder_path, exist_ok=True)

        if is_vbpl:
            # regex for vbpl
            match_id = re.search(r'/Attachments/(\d+)/', pdf_url)
        else:
            # regex for anle
            match_id = re.search(r'/UCMServer/(\w+)', pdf_url)

        if match_id:
            file_id = match_id.group(1)
        else:
            file_id = "noId"

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(pdf_url, verify=False)

        if is_vbpl:
            file_name_from_url = os.path.basename(pdf_url)
            pdf_file_name = urllib.parse.unquote_plus(file_name_from_url)
        else:
            pdf_file_name = get_anle_file_name(response)
            if not pdf_file_name:
                raise Exception(f"Failed to get file name for URL: {pdf_url}")

        file_name = f"({file_id})-{pdf_file_name}"
        file_path = os.path.join(folder_path, file_name)

        if response.status_code == 200:
            with open(file_path, 'wb') as pdf_file:
                pdf_file.write(response.content)
        else:
            raise Exception("Failed to download PDF from url")

        return file_path

    except Exception as e:
        print(f"Error processing URL: {pdf_url}")
        print(f"Error message: {str(e)}")
