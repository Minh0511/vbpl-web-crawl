import asyncio
import os
import re
from datetime import datetime
from http import HTTPStatus
from typing import Dict
import aiohttp
import pdfplumber
from bs4 import BeautifulSoup
from app.helper.constant import AnleSectionConst
from app.helper.custom_exception import CommonException
from app.helper.db import LocalSession
from app.helper.logger import setup_logger
from app.helper.utility import get_html_node_text
from app.model import Anle
from app.model import AnleSection
from app.service.get_pdf import get_document, is_pdf
from setting import setting
import aspose.words as aw
import py7zr

_logger = setup_logger('anle_logger', 'log/anle.log')


class AnleService:
    _api_base_url = setting.ANLE_BASE_URL

    @classmethod
    def get_headers(cls) -> Dict:
        return {'Content-Type': 'application/json'}

    @classmethod
    async def call(cls, method: str, url_path: str, query_params=None, json_data=None, timeout=90):
        url = cls._api_base_url + url_path
        headers = cls.get_headers()
        max_retries = 3
        for retry in range(max_retries):
            try:
                async with aiohttp.ClientSession(trust_env=True) as session:
                    async with session.request(method, url, params=query_params, json=json_data, timeout=timeout,
                                               headers=headers, verify_ssl=False) as resp:
                        await resp.text()
                if resp.status != HTTPStatus.OK:
                    _logger.warning(
                        "Calling Anle URL: %s, request_param %s, request_payload %s, http_code: %s, response: %s" %
                        (url, str(query_params), str(json_data), str(resp.status), resp.text))
                return resp
            except Exception as e:
                _logger.warning(f"Calling Anle URL: {url},"
                                f" request_params {str(query_params)}, request_body {str(json_data)},"
                                f" error {str(e)}")
                if retry < max_retries - 1:
                    _logger.warning(f"Retrying... (Attempt {retry + 1}/{max_retries})")
                    await asyncio.sleep(2 ** retry)  # Sleep for an increasing amount of time between retries
                else:
                    raise e

    @classmethod
    async def crawl_anle_info(cls, anle: Anle):
        url = f'/webcenter/portal/anle/chitietanle'
        query_params = {
            'dDocName': anle.doc_id,
            '_afrWindowMode': 0
        }
        try:
            resp = await cls.call(method='GET', url_path=url, query_params=query_params)
            if resp.status == HTTPStatus.OK:
                resp_text = await resp.text()
                soup = BeautifulSoup(resp_text, 'lxml')
                anle_info_node = soup.find('div', {'id': 'thuoctinh'})
                table_headers = anle_info_node.find_all('th')

                regex_dict = {
                    'serial_number': 'Số án lệ',
                    'title': 'Tên án lệ',
                    'adoption_date': 'Ngày thông qua',
                    'publication_date': 'Ngày công bố',
                    'publication_decision': 'Quyết định công bố',
                    'application_date': 'Ngày áp dụng',
                    'sector': 'Lĩnh vực',
                    'state': 'Trạng thái'
                }

                date_format = '%d/%m/%Y'

                def check_table_cell(field, html_node, input_anle: Anle):
                    if re.search(regex_dict[field], str(html_node)):
                        field_value_node = html_node.find_next_sibling('td')
                        if field_value_node:
                            if field == 'adoption_date' or field == 'publication_date' or field == 'application_date':
                                try:
                                    field_value = datetime.strptime(get_html_node_text(field_value_node), date_format)
                                except ValueError:
                                    field_value = None
                            else:
                                field_value = get_html_node_text(field_value_node)
                            setattr(input_anle, field, field_value)

                for header in table_headers:
                    for key in regex_dict.keys():
                        check_table_cell(key, header, anle)

                pdf_nodes = soup.find_all('div', {'id': 'filetaive'})
                pdf_links = []
                for node in pdf_nodes:
                    link_node = node.find('a')
                    if link_node is not None:
                        pdf_links.append(setting.ANLE_BASE_URL + link_node.get('href'))

                file_links = []
                if len(pdf_links) > 0:
                    for link in pdf_links:
                        file_link = get_document(link, False)
                        file_links.append(file_link)
                    anle.org_pdf_link = ' '.join(pdf_links)
                    anle.file_link = ' '.join(file_links)

                with LocalSession.begin() as session:
                    session.add(anle)

                for file_link in file_links:
                    file_id, anle_context, anle_solution, anle_content = cls.process_anle(file_link)
                    cls.to_anle_section_db(file_id, anle_context, anle_solution, anle_content)

        except Exception as e:
            _logger.exception(f'Crawl anle info {anle.id} {e}')
            raise CommonException(500, 'Crawl anle thuoc tinh')

    @classmethod
    async def crawl_all_anle(cls):
        url = f'/webcenter/portal/anle/anle'
        current_page = 1
        progress = 0
        while True:
            query_params = {
                'selectedPage': current_page,
                'docType': 'AnLe',
                'hieuLuc': 1,
            }
            total_records = 0
            try:
                resp = await cls.call(method='GET', url_path=url, query_params=query_params)
                if resp.status == HTTPStatus.OK:
                    soup = BeautifulSoup(await resp.text(), 'lxml')
                    total_records = soup.find('span', style="color: #2673b4").text
                    anle_attribute_list = soup.find_all('a', {
                        'class': 'thuoctinh-hover'
                    }, href=True)

                    for attr in anle_attribute_list:
                        href = attr['href']
                        anle_id = href.split('=')[-1]
                        with LocalSession.begin() as session:
                            statement = session.query(Anle).filter(Anle.doc_id == anle_id)
                            check_anle = session.execute(statement).all()
                            if len(check_anle) != 0:
                                progress += 1
                                _logger.info(f"Progress: {progress}/{total_records}")
                                continue

                        new_anle = Anle(doc_id=anle_id)
                        await cls.crawl_anle_info(new_anle)

                        # update progress
                        progress += 1
                        _logger.info(f"Progress: {progress}/{total_records}")

                if int(total_records) <= current_page * 10:
                    break
                current_page += 1
            except Exception as e:
                _logger.exception(f'Call anle search api {e}')
                raise CommonException(500, 'call anle search api')

    @classmethod
    def process_anle(cls, file_path: str):
        try:
            text = ''
            file_path_pattern = r'\((.*?)\)-'
            match_id = re.search(file_path_pattern, file_path)
            is_pdf_file = True

            if match_id:
                file_id = match_id.group(1)
            else:
                raise Exception("Failed to get file id")

            if not is_pdf(file_path):
                is_pdf_file = False
                doc = aw.Document(file_path)
                doc.save('temp.pdf')
                file_path = 'temp.pdf'

            with pdfplumber.open(file_path) as pdf_file:
                for page in pdf_file.pages:
                    page_text = page.extract_text()
                    text += page_text

            anle_context = cls.extract_pdf_content(AnleSectionConst.ANLE_CONTEXT, text)
            anle_solution = cls.extract_pdf_content(AnleSectionConst.ANLE_SOLUTION, text)
            anle_content = cls.extract_pdf_content(AnleSectionConst.ANLE_CONTENT, text)

            if not is_pdf_file:
                os.remove('temp.pdf')
                anle_content = anle_content.replace(AnleSectionConst.APOSE_WATERMARK, '')

            return file_id, anle_context, anle_solution, anle_content

        except Exception as e:
            _logger.exception(f'Failed to process anle pdf {file_path} {e}')
            raise Exception("Failed to process anle pdf", e)

    @classmethod
    def extract_pdf_content(cls, section: str, text: str):
        lines = text.split('\n')
        extracted_content = []

        inside_content = False

        for line in lines:
            if section in line:
                if inside_content:
                    continue
                else:
                    inside_content = True
            elif inside_content and section == AnleSectionConst.ANLE_CONTENT:
                extracted_content.append(line)
            elif inside_content and ":" in line:
                inside_content = False
            else:
                if inside_content:
                    extracted_content.append(line)

        if section == AnleSectionConst.ANLE_CONTENT:
            extracted_content = ' '.join(extracted_content)[:-1].replace("[", "\n[")
        else:
            extracted_content = ' '.join(extracted_content)

        return extracted_content

    @classmethod
    def to_anle_section_db(cls, file_id: str, anle_context: str, anle_solution: str, anle_content: str):
        with LocalSession.begin() as session:
            target_anle = session.query(Anle).filter(Anle.doc_id == file_id)
            for anle in target_anle:
                new_anle_section = AnleSection(
                    anle_id=anle.id,
                    context=anle_context,
                    solution=anle_solution,
                    content=anle_content,
                )
                session.add(new_anle_section)

    @classmethod
    async def fetch_anle_by_id(cls, anle_id):
        with LocalSession.begin() as session:
            target_anle = session.query(Anle).filter(Anle.doc_id == anle_id).order_by(Anle.updated_at.desc()).first()

        formatted_output = (
            f"ID trong bảng ghi: {target_anle.id},\n"
            f"ID án lệ: {target_anle.doc_id},\n"
            f"Đường dẫn lưu file: {target_anle.file_link},\n"
            f"Tên án lệ: {target_anle.title},\n"
            f"Số án lệ: {target_anle.serial_number},\n"
            f"Ngày thông qua: {target_anle.adoption_date},\n"
            f"Ngày áp dụng: {target_anle.application_date},\n"
            f"Ngày hết hiệu lực: {target_anle.expiration_date},\n"
            f"Ngày công bố: {target_anle.publication_date},\n"
            f"Trạng thái: {target_anle.state},\n"
            f"Lĩnh vực: {target_anle.sector},\n"
            f"Quyết định công bố: {target_anle.publication_decision},\n"
            f"Đường dẫn đến link gốc: {target_anle.org_pdf_link},\n"
        )

        print(formatted_output)
        return target_anle

    @classmethod
    async def get_anle_preview(cls):
        with LocalSession.begin() as session:
            query = session.query(Anle)

        sql_query = str(query)
        sql_folder_path = 'documents/preview/anle'
        os.makedirs(sql_folder_path, exist_ok=True)
        sql_file_path = os.path.join(sql_folder_path, 'anle_preview_script.sql')

        with open(sql_file_path, 'w') as f:
            f.write(sql_query)

        file_links = []

        target_records = query.all()
        for record in target_records:
            if record.file_link is not None:
                file_links.append(record.file_link)

        output_rar_filepath = os.path.join(sql_folder_path, 'preview_anle.rar')
        with py7zr.SevenZipFile(output_rar_filepath, 'w') as archive:
            for file_link in file_links:
                archive.write(file_link)
