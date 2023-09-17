import re
import pdfplumber

from app.helper.constant import Anle


def process_anle(file_path):
    try:
        with pdfplumber.open(file_path) as pdf_file:
            text = ''

            for page in pdf_file.pages:
                page_text = page.extract_text()
                text += page_text

        anle_context = extract_pdf_content(Anle.ANLE_CONTEXT, text)
        anle_solution = extract_pdf_content(Anle.ANLE_SOLUTION, text)
        anle_content = extract_pdf_content(Anle.ANLE_CONTENT, text)

        file_path_pattern = r'\((.*?)\)-'
        match_id = re.search(file_path_pattern, file_path)

        if match_id:
            file_id = match_id.group(1)
        else:
            raise Exception("Failed to get file id")

        return file_id, anle_context, anle_solution, anle_content

    except Exception as e:
        print(e)


def extract_pdf_content(content_type, text):
    lines = text.split('\n')
    extracted_content = []

    inside_content = False

    for line in lines:
        if content_type in line:
            if inside_content:
                continue
            else:
                inside_content = True
        elif inside_content and content_type == Anle.ANLE_CONTENT:
            extracted_content.append(line)
        elif inside_content and ":" in line:
            inside_content = False
        else:
            if inside_content:
                extracted_content.append(line)

    if content_type == Anle.ANLE_CONTENT:
        extracted_content = ' '.join(extracted_content)[:-1].replace("[", "\n[")
    else:
        extracted_content = ' '.join(extracted_content)

    return extracted_content
