import logging
import math

import copy
import os
from datetime import datetime
from http import HTTPStatus
from typing import Dict

import pdfplumber
import requests

import re

from app.helper.constant import AnleSectionConst
from app.model import AnleSection

from app.entity.vbpl import VbplFullTextField
from app.helper.custom_exception import CommonException
from app.helper.enum import VbplTab, VbplType
from app.model import VbplToanVan, Vbpl, VbplRelatedDocument, VbplDocMap, Anle
from app.service.get_pdf import get_pdf
from setting import setting
from app.helper.utility import convert_dict_to_pascal, get_html_node_text
from app.helper.db import LocalSession
from urllib.parse import quote
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


class AnleService:
    _api_base_url = setting.ANLE_BASE_URL

    @classmethod
    def get_headers(cls) -> Dict:
        return {'Content-Type': 'application/json'}

    @classmethod
    def call(cls, method: str, url_path: str, query_params=None, json_data=None, timeout=30):
        url = cls._api_base_url + url_path
        headers = cls.get_headers()
        try:
            resp: requests.Response = requests.request(method, url, params=query_params, json=json_data,
                                                       headers=headers, timeout=timeout, verify=False)
            if resp.status_code != 200:
                _logger.warning(
                    "Calling VBPL URL: %s, request_param %s, request_payload %s, http_code: %s, response: %s" %
                    (url, str(query_params), str(json_data), str(resp.status_code), resp.text))
            return resp
        except Exception as e:
            _logger.warning(f"Calling VBPL URL: {url},"
                            f" request_params {str(query_params)}, request_body {str(json_data)},"
                            f" error {str(e)}")
            raise e

    @classmethod
    def crawl_anle_info(cls, anle: Anle):
        url = f'/webcenter/portal/anle/chitietanle'
        query_params = {
            'dDocName': anle.doc_id
        }
        try:
            resp = cls.call(method='GET', url_path=url, query_params=query_params)
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Crawl anle thuoc tinh')
        if resp.status_code == HTTPStatus.OK:
            soup = BeautifulSoup(resp.text, 'lxml')
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

            def check_table_cell(field, node, input_anle: Anle):
                if re.search(regex_dict[field], str(node)):
                    field_value_node = node.find_next_sibling('td')
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

            if len(pdf_links) > 0:
                file_links = []
                for link in pdf_links:
                    file_links.append(get_pdf(link, False))
                anle.org_pdf_link = ' '.join(pdf_links)
                anle.file_link = ' '.join(file_links)

            with LocalSession.begin() as session:
                session.add(anle)

            print(anle)

    @classmethod
    def crawl_anle_ids(cls):
        url = f'/webcenter/portal/anle/anle'
        current_page = 1
        anle_ids = []
        while True:
            query_params = {
                'selectedPage': current_page,
                'docType': 'AnLe',
                'hieuLuc': 1,
            }
            total_records = 0
            try:
                resp = cls.call(method='GET', url_path=url, query_params=query_params)
            except Exception as e:
                _logger.exception(e)
                raise CommonException(500, 'call anle search api')
            if resp.status_code == HTTPStatus.OK:
                soup = BeautifulSoup(resp.text, 'lxml')
                total_records = soup.find('span', style="color: #2673b4").text
                anle_attribute_list = soup.find_all('a', {
                    'class': 'thuoctinh-hover'
                }, href=True)

                for attr in anle_attribute_list:
                    href = attr['href']
                    anle_id = href.split('=')[-1]
                    anle_ids.append(anle_id)

            if int(total_records) <= current_page * 10:
                break
            current_page += 1

        print("anle ids:", list(set(anle_ids)))
        print("number of an le:", len(list(set(anle_ids))))

        return list(set(anle_ids))

    @classmethod
    def process_anle(cls, file_path: str):
        try:
            with pdfplumber.open(file_path) as pdf_file:
                text = ''

                for page in pdf_file.pages:
                    page_text = page.extract_text()
                    text += page_text

            anle_context = cls.extract_pdf_content(AnleSectionConst.ANLE_CONTEXT, text)
            anle_solution = cls.extract_pdf_content(AnleSectionConst.ANLE_SOLUTION, text)
            anle_content = cls.extract_pdf_content(AnleSectionConst.ANLE_CONTENT, text)

            file_path_pattern = r'\((.*?)\)-'
            match_id = re.search(file_path_pattern, file_path)

            if match_id:
                file_id = match_id.group(1)
            else:
                raise Exception("Failed to get file id")

            return file_id, anle_context, anle_solution, anle_content

        except Exception as e:
            print(e)

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