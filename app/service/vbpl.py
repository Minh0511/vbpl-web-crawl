import logging
import math
import re
from http import HTTPStatus
from typing import Dict

import requests

from app.helper.custom_exception import CommonException
from app.helper.enum import VbplTab
from setting import setting
from app.helper.utility import convert_dict_to_pascal
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)
find_id_regex = '(?<=ItemID=).*?(?=&)'


class VbplService:
    _api_base_url = setting.VBPl_BASE_URL
    _default_row_per_page = 10

    @classmethod
    def get_headers(cls) -> Dict:
        return {'Content-Type': 'application/json'}

    @classmethod
    def call(cls, method: str, url_path: str, query_params=None, json_data=None, timeout=30, is_slow=False):
        url = cls._api_base_url + url_path
        headers = cls.get_headers()
        try:
            resp: requests.Response = requests.request(method, url, params=query_params, json=json_data,
                                                       headers=headers, timeout=timeout)
            r = resp.json()
            if resp.status_code != 200 or (resp.status_code == 200 and resp.json().get('code') != 200):
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
    def get_total_doc(cls):
        try:
            query_params = convert_dict_to_pascal({
                'is_viet_namese': True,
                'row_per_page': cls._default_row_per_page,
                'page': 2
            })

            resp = cls.call(method='GET',
                            url_path=f'/VBQPPL_UserControls/Publishing_22/TimKiem/p_KetQuaTimKiemVanBan.aspx',
                            query_params=query_params)
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Get total doc')
        if resp.status_code == HTTPStatus.OK:
            soup = BeautifulSoup(resp.text, 'lxml')
            message = soup.find('div', {'class': 'message'})
            return int(message.find('strong').string)

    @classmethod
    def crawl_vbpl_all(cls):
        total_doc = cls.get_total_doc()
        total_pages = math.ceil(total_doc / cls._default_row_per_page)
        prev_id_set = set()

        for i in range(total_pages):
            query_params = convert_dict_to_pascal({
                'is_viet_namese': True,
                'row_per_page': cls._default_row_per_page,
                'page': i + 1
            })

            try:
                resp = cls.call(method='GET',
                                url_path=f'/VBQPPL_UserControls/Publishing_22/TimKiem/p_KetQuaTimKiemVanBan.aspx',
                                query_params=query_params)
            except Exception as e:
                _logger.exception(e)
                raise CommonException(500, 'Crawl all doc')
            if resp.status_code == HTTPStatus.OK:
                soup = BeautifulSoup(resp.text, 'lxml')
                titles = soup.find_all('p', {"class": "title"})
                check_last_page = False
                id_set = set()

                for title in titles:
                    link = title.find('a')
                    doc_id = int(re.findall(find_id_regex, link.get('href'))[0])
                    if doc_id in prev_id_set:
                        check_last_page = True
                        break
                    id_set.add(doc_id)

                if check_last_page:
                    break

                prev_id_set = id_set

    @classmethod
    def crawl_vbpl_toanvan(cls, vbpl_id):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.FULL_TEXT}.aspx'
        query_params = {
            'ItemID': vbpl_id
        }

        try:
            resp = cls.call(method='GET', url_path=aspx_url, query_params=query_params)
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Crawl vbpl toan van')

        if resp.status_code == HTTPStatus.OK:
            soup = BeautifulSoup(resp.text, 'lxml')
            fulltext = soup.find('div', {"class": "toanvancontent"})

            find_section_regex = '>((Điều)|(Điều thứ))'
            find_chapter_regex = '>Chương'
            find_part_regex = '>Mục'
            find_mini_part_regex = '>Tiểu mục'

            lines = fulltext.find_all('p')

            for line in lines:
                if re.search(find_section_regex, str(line)):
                    line_content = str(line.text)
                    print(re.findall('(?<=Điều )\\d+', line_content), line_content)

                    next_node = line
                    while True:
                        next_node = next_node.find_next_sibling('p')

                        if next_node is None:
                            break

                        if re.search(find_chapter_regex, str(next_node)) or re.search(find_part_regex, str(next_node)):
                            next_node = next_node.find_next_sibling('p')
                            continue
                        if re.search(find_section_regex, str(next_node)):
                            break
                        print(next_node.text)
