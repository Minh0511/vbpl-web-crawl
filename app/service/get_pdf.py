import logging
import os
import re
import urllib.parse
import requests
import requests.packages
import urllib3.exceptions

logging.basicConfig(filename="log/pdf.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
_logger = logging.getLogger(__name__)


def get_anle_file_name(response):
    content_disposition = response.headers.get('Content-Disposition')
    if content_disposition:
        match_file_name = re.search(r'filename=(.*?)(?:;|$)', content_disposition)
        if match_file_name:
            return match_file_name.group(1)

    return None


def get_document(document_url, is_vbpl, file_id=None, is_pdf_file=None):
    document_url = clean_extension(document_url)
    try:
        pdf_folder_path = 'documents/pdf/anle_pdf'
        doc_folder_path = 'documents/doc/anle_doc'
        if is_vbpl:
            pdf_folder_path = 'documents/pdf/vbpl_pdf'
            doc_folder_path = 'documents/doc/vbpl_doc'

        os.makedirs(pdf_folder_path, exist_ok=True)
        os.makedirs(doc_folder_path, exist_ok=True)

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(document_url, verify=False)

        if is_vbpl:
            file_name_from_url = os.path.basename(document_url)
            document_file_name = urllib.parse.unquote_plus(file_name_from_url)
        else:
            document_file_name = get_anle_file_name(response).replace(" ", "_")
            if not document_file_name:
                raise Exception(f"Failed to get file name for URL: {document_url}")

        decoded_file_name = urllib.parse.unquote(document_file_name)

        if file_id is None:
            file_id = get_file_id(document_url, is_vbpl)
            file_name = f"({file_id})-{decoded_file_name.replace(' ', '_').replace('%', '_')}"
        else:
            if is_pdf_file:
                file_name = f"{file_id}.pdf"
            else:
                file_name = f"{file_id}.doc"

        if is_pdf(file_name):
            file_path = os.path.join(pdf_folder_path, file_name)
        else:
            file_path = os.path.join(doc_folder_path, file_name)

        if response.status_code == 200:
            with open(file_path, 'wb') as pdf_file:
                pdf_file.write(response.content)
        else:
            raise Exception(f"Failed to download PDF from url {response.status_code}")

        return file_path

    except Exception as e:
        _logger.exception(f'Error processing URL: {document_url} {e}')


def is_pdf(file_name):
    pattern = r'\.pdf$'
    return re.search(pattern, file_name, re.IGNORECASE) is not None


def get_file_id(document_url, is_vbpl):
    if is_vbpl:
        # regex for vbpl
        match_id = re.search(r'/Attachments/(\d+)/', document_url)
    else:
        # regex for anle
        match_id = re.search(r'/UCMServer/(\w+)', document_url)

    if match_id:
        file_id = match_id.group(1)
    else:
        file_id = "noId"
    return file_id


def clean_extension(filename):
    pattern = r'\.{2}(docx?|pdf)$'

    cleaned_filename = re.sub(pattern, r'.\1', filename)

    return cleaned_filename
