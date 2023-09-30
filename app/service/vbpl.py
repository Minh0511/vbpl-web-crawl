import asyncio
import logging
import math
import re
import copy
from datetime import datetime
from http import HTTPStatus
from typing import Dict
from sqlalchemy import update

import aiohttp
import yarl
import concurrent.futures

from app.entity.vbpl import VbplFullTextField
from app.helper.custom_exception import CommonException
from app.helper.enum import VbplTab, VbplType
from time import sleep
from app.helper.logger import setup_logger
from app.model import VbplToanVan, Vbpl, VbplRelatedDocument, VbplDocMap
from app.service.get_pdf import get_document
from setting import setting
from app.helper.utility import convert_dict_to_pascal, get_html_node_text, convert_datetime_to_str, \
    concetti_query_params_url_encode
from app.helper.db import LocalSession
from urllib.parse import quote
import Levenshtein
from bs4 import BeautifulSoup

_logger = setup_logger('vbpl_logger', 'log/vbpl.log')
find_id_regex = '(?<=ItemID=)\\d+'


class VbplService:
    _api_base_url = setting.VBPl_BASE_URL
    _default_row_per_page = 130
    _max_threads = 8
    _find_big_part_regex = '^((Phần)|(Phần thứ)) (nhất|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)$'
    _find_section_regex = '^((Điều)|(Điều thứ)) \\d+'
    _find_chapter_regex = '^Chương [IVX]+'
    _find_part_regex = '^Mục [IVX]+'
    _find_part_regex_2 = '^Mu.c [IVX]+'
    _find_mini_part_regex = '^Tiểu mục [IVX]+'
    _empty_related_doc_msg = 'Nội dung đang cập nhật'
    _concetti_base_url = setting.CONCETTI_BASE_URL
    _tvpl_base_url = setting.TVPL_BASE_URL
    _cong_bao_base_url = setting.CONG_BAO_BASE_URL

    @classmethod
    def get_headers(cls) -> Dict:
        return {'Content-Type': 'application/json'}

    @classmethod
    async def call(cls, method: str, url_path: str, query_params=None, json_data=None, timeout=90):
        url = cls._api_base_url + url_path
        headers = cls.get_headers()
        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.request(method, url, params=query_params, json=json_data, timeout=timeout,
                                           headers=headers) as resp:
                    await resp.text()
            if resp.status != HTTPStatus.OK:
                _logger.warning(
                    "Calling VBPL URL: %s, request_param %s, request_payload %s, http_code: %s, response: %s" %
                    (url, str(query_params), str(json_data), str(resp.status), resp.text))
            return resp
        except Exception as e:
            _logger.warning(f"Calling VBPL URL: {url},"
                            f" request_params {str(query_params)}, request_body {str(json_data)},"
                            f" error {str(e)}")

    @classmethod
    async def get_total_doc(cls, vbpl_type: VbplType):
        try:
            query_params = convert_dict_to_pascal({
                'row_per_page': cls._default_row_per_page,
                'page': 2,
            })

            resp = await cls.call(method='GET',
                                  url_path=f'/VBQPPL_UserControls/Publishing_22/TimKiem/p_{vbpl_type.value}.aspx?IsVietNamese=True',
                                  query_params=query_params)
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                message = soup.find('div', {'class': 'message'})
                return int(message.find('strong').string)
        except Exception as e:
            _logger.exception(f'Get total vbpl doc {e}')
            raise CommonException(500, 'Get total doc')

    @classmethod
    async def crawl_all_vbpl(cls, vbpl_type: VbplType):
        total_doc = await cls.get_total_doc(vbpl_type)
        total_pages = 1000
        full_id_list = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=cls._max_threads) as executor:
            info_and_fulltext_coroutines = [cls.crawl_vbpl_in_one_page(page, full_id_list, vbpl_type) for page in
                                            range(1, total_pages + 1)]
            executor.map(asyncio.run, info_and_fulltext_coroutines)

        with concurrent.futures.ThreadPoolExecutor(max_workers=cls._max_threads) as executor:
            related_doc_coroutines = [cls.crawl_vbpl_related_doc(doc_id) for doc_id in full_id_list]
            executor.map(asyncio.run, related_doc_coroutines)

        with concurrent.futures.ThreadPoolExecutor(max_workers=cls._max_threads) as executor:
            doc_map_coroutines = [cls.crawl_vbpl_doc_map(doc_id, vbpl_type) for doc_id in full_id_list]
            executor.map(asyncio.run, doc_map_coroutines)

        # for i in range(1, total_pages):
        #     await cls.crawl_vbpl_in_one_page(i, full_id_list, vbpl_type)

        # for doc_id in full_id_list:
        #     await cls.crawl_vbpl_related_doc(doc_id)
        #     await cls.crawl_vbpl_doc_map(doc_id, vbpl_type)

    @classmethod
    async def crawl_vbpl_in_one_page(cls, page, full_id_list, vbpl_type: VbplType):
        query_params = convert_dict_to_pascal({
            'row_per_page': cls._default_row_per_page,
            'page': page
        })
        progress = 0
        max_progress = cls._default_row_per_page

        try:
            resp = await cls.call(method='GET',
                                  url_path=f'/VBQPPL_UserControls/Publishing_22/TimKiem/p_{vbpl_type.value}.aspx?IsVietNamese=True',
                                  query_params=query_params)
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                titles = soup.find_all('p', {"class": "title"})
                sub_titles = soup.find_all('div', {'class': "des"})
                id_set = set()

                for j in range(len(titles)):
                    title = titles[j]
                    sub_title = sub_titles[j]

                    link = title.find('a')
                    doc_id = int(re.findall(find_id_regex, link.get('href'))[0])

                    _logger.info(f"Crawling vbpl {doc_id}")
                    id_set.add(doc_id)
                    full_id_list.append(doc_id)

                    with LocalSession.begin() as session:
                        check_vbpl = session.query(Vbpl).filter(Vbpl.id == doc_id).first()
                        if check_vbpl is not None:
                            progress += 1
                            _logger.info(f'Finished crawling vbpl {doc_id}')
                            _logger.info(f"Page {page} progress: {progress}/{max_progress}")
                            continue

                    new_vbpl = Vbpl(
                        id=doc_id,
                        title=get_html_node_text(link),
                        sub_title=get_html_node_text(sub_title)
                    )
                    if vbpl_type == VbplType.PHAP_QUY:
                        await cls.crawl_vbpl_phapquy_info(new_vbpl)
                        vbpl_fulltext = await cls.crawl_vbpl_phapquy_fulltext(new_vbpl)
                        await cls.search_concetti(new_vbpl)

                        with LocalSession.begin() as session:
                            session.add(new_vbpl)
                            if vbpl_fulltext is not None:
                                for fulltext_section in vbpl_fulltext:
                                    check_fulltext = session.query(VbplToanVan).filter(
                                        VbplToanVan.vbpl_id == fulltext_section.vbpl_id,
                                        VbplToanVan.section_number == fulltext_section.section_number).first()
                                    if check_fulltext is None:
                                        session.add(fulltext_section)

                    elif vbpl_type == VbplType.HOP_NHAT:
                        await cls.crawl_vbpl_hopnhat_info(new_vbpl)
                        await cls.crawl_vbpl_hopnhat_fulltext(new_vbpl)
                        await cls.search_concetti(new_vbpl)
                        vbpl_fulltext = await cls.additional_html_crawl(new_vbpl)

                        with LocalSession.begin() as session:
                            session.add(new_vbpl)
                            if vbpl_fulltext is not None:
                                for fulltext_section in vbpl_fulltext:
                                    check_fulltext = session.query(VbplToanVan).filter(
                                        VbplToanVan.vbpl_id == fulltext_section.vbpl_id,
                                        VbplToanVan.section_number == fulltext_section.section_number).first()
                                    if check_fulltext is None:
                                        session.add(fulltext_section)

                    # update progress
                    progress += 1
                    _logger.info(f'Finished crawling vbpl {doc_id}')
                    _logger.info(f"Page {page} progress: {progress}/{max_progress}")
            sleep(3)
        except Exception as e:
            _logger.exception(f'Crawl all doc in page {page} {e}')
            raise CommonException(500, 'Crawl all doc')

    @classmethod
    def update_vbpl_phapquy_fulltext(cls, line, fulltext_obj: VbplFullTextField):
        line_content = get_html_node_text(line)
        check = False

        if re.search(cls._find_big_part_regex, line_content):
            current_big_part_number_search = re.search('(?<=Phần thứ ).+', line_content)
            fulltext_obj.current_big_part_number = line_content[current_big_part_number_search.span()[0]:]
            next_node = line.find_next_sibling('p')
            fulltext_obj.current_big_part_name = get_html_node_text(next_node)

            fulltext_obj.reset_part()
            check = True

        if re.search(cls._find_chapter_regex, line_content):
            fulltext_obj.current_chapter_number = re.findall('(?<=Chương ).+', line_content)[0]
            next_node = line.find_next_sibling('p')
            fulltext_obj.current_chapter_name = get_html_node_text(next_node)

            fulltext_obj.reset_part()
            check = True

        if re.search(cls._find_part_regex, line_content) or re.search(cls._find_part_regex_2, line_content):
            if re.search(cls._find_part_regex, line_content):
                fulltext_obj.current_part_number = re.findall('(?<=Mục ).+', line_content)[0]
            else:
                fulltext_obj.current_part_number = re.findall('(?<=Mu.c ).+', line_content)[0]
            next_node = line.find_next_sibling('p')
            fulltext_obj.current_part_name = get_html_node_text(next_node)
            check = True

        if re.search(cls._find_mini_part_regex, line_content):
            fulltext_obj.current_mini_part_number = re.findall('(?<=Tiểu mục ).+', line_content)[0]
            next_node = line.find_next_sibling('p')
            fulltext_obj.current_mini_part_name = get_html_node_text(next_node)
            check = True

        return fulltext_obj, check

    @classmethod
    def process_html_full_text(cls, vbpl: Vbpl, lines):
        vbpl_fulltext_obj = VbplFullTextField()
        results = []

        for line in lines:
            line_content = get_html_node_text(line)
            if re.search(cls._find_section_regex, line_content):
                break

            vbpl_fulltext_obj, check = cls.update_vbpl_phapquy_fulltext(line, vbpl_fulltext_obj)
            if check:
                continue

        for line in lines:
            line_content = get_html_node_text(line)

            if re.search(cls._find_section_regex, line_content):
                section_number_search = re.search('\\b\\d+', line_content)
                section_number = int(section_number_search.group())

                section_name = line_content[section_number_search.span()[1]:]
                section_name_refined = None
                section_name_search = re.search('\\b\\w', section_name)
                if section_name_search:
                    section_name_refined = section_name[section_name_search.span()[0]:]

                current_fulltext_config = copy.deepcopy(vbpl_fulltext_obj)
                content = []
                if section_name_refined is not None and len(section_name_refined) >= 400:
                    content.append(section_name_refined)
                    section_name_refined = None

                next_node = line
                while True:
                    next_node = next_node.find_next_sibling('p')

                    if next_node is None:
                        break

                    vbpl_fulltext_obj, check = cls.update_vbpl_phapquy_fulltext(next_node, vbpl_fulltext_obj)
                    if check:
                        next_node = next_node.find_next_sibling('p')
                        continue

                    node_content = get_html_node_text(next_node)
                    if re.search(cls._find_section_regex, node_content) or re.search('_{2,}', node_content):
                        section_content = '\n'.join(content)

                        new_fulltext_section = VbplToanVan(
                            vbpl_id=vbpl.id,
                            section_number=section_number,
                            section_name=section_name_refined,
                            section_content=section_content,
                            chapter_name=current_fulltext_config.current_chapter_name,
                            chapter_number=current_fulltext_config.current_chapter_number,
                            mini_part_name=current_fulltext_config.current_mini_part_name,
                            mini_part_number=current_fulltext_config.current_mini_part_number,
                            part_name=current_fulltext_config.current_part_name,
                            part_number=current_fulltext_config.current_part_number,
                            big_part_name=current_fulltext_config.current_big_part_name,
                            big_part_number=current_fulltext_config.current_big_part_number
                        )
                        results.append(new_fulltext_section)
                        break

                    content.append(get_html_node_text(next_node))
        return results

    @classmethod
    async def crawl_vbpl_phapquy_fulltext(cls, vbpl: Vbpl):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.FULL_TEXT.value}.aspx'
        query_params = {
            'ItemID': vbpl.id
        }
        results = []

        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)

            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                fulltext = soup.find('div', {"class": "toanvancontent"})

                if fulltext is None:
                    return await cls.additional_html_crawl(vbpl)

                vbpl.html = str(fulltext)

                lines = fulltext.find_all('p')
                if len(lines) == 0:
                    lines = fulltext.find_all('div')
                if len(lines) == 0:
                    return await cls.additional_html_crawl(vbpl)
                results = cls.process_html_full_text(vbpl, lines)
        except Exception as e:
            _logger.exception(f'Crawl vbpl phapquy fulltext {vbpl.id} {e}')
            raise CommonException(500, 'Crawl vbpl toan van')

        return results

    @classmethod
    async def crawl_vbpl_hopnhat_fulltext(cls, vbpl: Vbpl):
        if vbpl.org_pdf_link is not None and vbpl.org_pdf_link.strip() != '':
            return

        aspx_url = f'/TW/Pages/vbpq-{VbplTab.FULL_TEXT_HOP_NHAT.value}.aspx'
        query_params = {
            'ItemID': vbpl.id
        }

        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                vbpl_view = soup.find('div', {'class': 'vbProperties'})
                document_view_object = vbpl_view.find('object')
                if document_view_object is not None:
                    document_link = re.findall('.+.pdf', document_view_object.get('data'))[0]
                    vbpl.org_pdf_link = setting.VBPL_PDF_BASE_URL + document_link
                    vbpl.file_link = get_document(vbpl.org_pdf_link, True)
                else:
                    aspx_url = f'/TW/Pages/vbpq-{VbplTab.FULL_TEXT_HOP_NHAT_2.value}.aspx'
                    query_params = {
                        'ItemID': vbpl.id
                    }

                    resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)

                    if resp.status == HTTPStatus.OK:
                        soup = BeautifulSoup(await resp.text(), 'lxml')
                        vbpl_view = soup.find('div', {'class': 'vbProperties'})
                        pdf_view_object = vbpl_view.find('object')
                        if pdf_view_object is not None:
                            pdf_link = re.findall('.+.pdf', pdf_view_object.get('data'))[0]
                            vbpl.org_pdf_link = setting.VBPL_PDF_BASE_URL + pdf_link
                            vbpl.file_link = get_document(vbpl.org_pdf_link, True)
        except Exception as e:
            _logger.exception(f'Crawl vbpl hopnhat fulltext {vbpl.id} {e}')
            raise CommonException(500, 'Crawl vbpl hop nhat toan van')

    @classmethod
    async def crawl_vbpl_hopnhat_info(cls, vbpl: Vbpl):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.ATTRIBUTE_HOP_NHAT.value}.aspx'
        query_params = {
            'ItemID': vbpl.id
        }

        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')

                properties = soup.find('div', {"class": "vbProperties"})
                files = soup.find('ul', {'class': 'fileAttack'})

                table_rows = properties.find_all('tr')
                date_format = '%d/%m/%Y'

                bread_crumbs = soup.find('div', {"class": "box-map"})
                title = bread_crumbs.find('a', {"href": ""})
                vbpl.title = title.text.strip()
                sub_title = soup.find('td', {'class': 'title'})
                vbpl.sub_title = sub_title.text.strip()

                regex_dict = {
                    'serial_number': 'Số ký hiệu',
                    'effective_date': 'Ngày xác thực',
                    'gazette_date': 'Ngày đăng công báo',
                    'issuing_authority': 'Cơ quan ban hành',
                    'doc_type': 'Loại VB được sửa đổi bổ sung'
                }

                def check_table_cell(field, node, input_vbpl: Vbpl):
                    if re.search(regex_dict[field], str(node)):
                        field_value_node = node.find_next_sibling('td')
                        if field_value_node:
                            if field == 'effective_date' or field == 'gazette_date':
                                try:
                                    field_value = datetime.strptime(get_html_node_text(field_value_node), date_format)
                                except ValueError:
                                    field_value = None
                            else:
                                field_value = get_html_node_text(field_value_node)
                            setattr(input_vbpl, field, field_value)

                for row in table_rows:
                    table_cells = row.find_all('td')

                    for cell in table_cells:
                        for key in regex_dict.keys():
                            check_table_cell(key, cell, vbpl)

                file_urls = []
                file_links = files.find_all('li')

                for link in file_links:
                    link_node = link.find_all('a')[0]
                    if re.search('.+.pdf', get_html_node_text(link_node)) \
                            or re.search('.+.doc', get_html_node_text(link_node)) \
                            or re.search('.+.docx', get_html_node_text(link_node)):
                        href = link_node['href']
                        file_url = href
                        if re.search('javascript:downloadfile', href):
                            file_url = href[len('javascript:downloadfile('):-2].split(',')[1][1:-1]
                        file_urls.append(quote(setting.VBPL_PDF_BASE_URL + file_url, safe='/:?'))
                if len(file_urls) > 0:
                    local_links = []
                    for url in file_urls:
                        doc_link = get_document(url, True)
                        if doc_link is not None:
                            local_links.append(get_document(url, True))
                    if len(local_links) > 0:
                        vbpl.file_link = ' '.join(local_links)
                    vbpl.org_pdf_link = ' '.join(file_urls)
        except Exception as e:
            _logger.exception(f'Crawl vbpl hopnhat info {vbpl.id} {e}')
            raise CommonException(500, 'Crawl vbpl thuoc tinh')

    @classmethod
    async def crawl_vbpl_phapquy_info(cls, vbpl: Vbpl):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.ATTRIBUTE.value}.aspx'
        query_params = {
            'ItemID': vbpl.id
        }

        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')

                properties = soup.find('div', {"class": "vbProperties"})
                info = soup.find('div', {'class': 'vbInfo'})
                files = soup.find('ul', {'class': 'fileAttack'})

                bread_crumbs = soup.find('div', {"class": "box-map"})
                title = bread_crumbs.find('a', {"href": ""})
                vbpl.title = title.text.strip()
                sub_title = soup.find('td', {'class': 'title'})
                vbpl.sub_title = sub_title.text.strip()

                table_rows = properties.find_all('tr')

                state_regex = 'Hiệu lực:'
                expiration_date_regex = 'Ngày hết hiệu lực:'

                date_format = '%d/%m/%Y'

                regex_dict = {
                    'serial_number': 'Số ký hiệu',
                    'issuance_date': 'Ngày ban hành',
                    'effective_date': 'Ngày có hiệu lực',
                    'gazette_date': 'Ngày đăng công báo',
                    'issuing_authority': 'Cơ quan ban hành',
                    'applicable_information': 'Thông tin áp dụng',
                    'doc_type': 'Loại văn bản'
                }

                def check_table_cell(field, node, input_vbpl: Vbpl):
                    if re.search(regex_dict[field], str(node)):
                        field_value_node = node.find_next_sibling('td')
                        if field_value_node:
                            if field == 'issuance_date' or field == 'effective_date' or field == 'gazette_date':
                                try:
                                    field_value = datetime.strptime(get_html_node_text(field_value_node), date_format)
                                except ValueError:
                                    field_value = None
                            else:
                                field_value = get_html_node_text(field_value_node)
                            setattr(input_vbpl, field, field_value)

                for row in table_rows:
                    table_cells = row.find_all('td')

                    for cell in table_cells:
                        for key in regex_dict.keys():
                            check_table_cell(key, cell, vbpl)

                info_rows = info.find_all('li')

                for row in info_rows:
                    if re.search(state_regex, str(row)):
                        vbpl.state = get_html_node_text(row)[len(state_regex):].strip()
                    elif re.search(expiration_date_regex, str(row)):
                        date_content = get_html_node_text(row)[len(expiration_date_regex):].strip()
                        vbpl.expiration_date = datetime.strptime(date_content, date_format)

                file_urls = []
                file_links = files.find_all('li')

                for link in file_links:
                    link_node = link.find_all('a')[0]
                    link_content = get_html_node_text(link_node)
                    if re.search('.+.pdf', link_content) \
                            or re.search('.+.doc', link_content) \
                            or re.search('.+.docx', link_content):
                        href = link_node['href']
                        file_url = href[len('javascript:downloadfile('):-2].split(',')[1][1:-1]
                        file_urls.append(quote(setting.VBPL_PDF_BASE_URL + file_url, safe='/:?'))

                if len(file_urls) > 0:
                    local_links = []
                    for url in file_urls:
                        doc_link = get_document(url, True)
                        if doc_link is not None:
                            local_links.append(get_document(url, True))
                    if len(local_links) > 0:
                        vbpl.file_link = ' '.join(local_links)
                    vbpl.org_pdf_link = ' '.join(file_urls)
        except Exception as e:
            _logger.exception(f'Crawl vbpl phapquy info {vbpl.id} {e}')
            raise CommonException(500, 'Crawl vbpl thuoc tinh')

    @classmethod
    async def crawl_vbpl_related_doc(cls, vbpl_id):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.RELATED_DOC.value}.aspx'
        query_params = {
            'ItemID': vbpl_id
        }
        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')

                related_doc_node = soup.find('div', {'class': 'vbLienQuan'})
                if related_doc_node is None or re.search(cls._empty_related_doc_msg,
                                                         get_html_node_text(related_doc_node)):
                    return

                doc_type_node = related_doc_node.find_all('td', {'class': 'label'})

                for node in doc_type_node:
                    doc_type = get_html_node_text(node)
                    related_doc_list_node = node.find_next_sibling('td').find('ul', {'class': 'listVB'})

                    related_doc_list = related_doc_list_node.find_all('p', {'class': 'title'})
                    for doc in related_doc_list:
                        link = doc.find('a')
                        doc_id = int(re.findall(find_id_regex, link.get('href'))[0])
                        new_vbpl_related_doc = VbplRelatedDocument(
                            source_id=vbpl_id,
                            related_id=doc_id,
                            doc_type=doc_type
                        )
                        with LocalSession.begin() as session:
                            check_related_doc = session.query(VbplRelatedDocument).filter(
                                VbplRelatedDocument.source_id == new_vbpl_related_doc.source_id,
                                VbplRelatedDocument.related_id == new_vbpl_related_doc.related_id).first()
                            if check_related_doc is None:
                                session.add(new_vbpl_related_doc)
            sleep(1)
        except Exception as e:
            _logger.exception(f'Crawl vbpl related doc {vbpl_id} {e}')
            raise CommonException(500, 'Crawl vbpl van ban lien quan')

    @classmethod
    async def crawl_vbpl_doc_map(cls, vbpl_id, vbpl_type: VbplType):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.DOC_MAP.value}.aspx'
        if vbpl_type == VbplType.HOP_NHAT:
            aspx_url = f'/TW/Pages/vbpq-{VbplTab.DOC_MAP_HOP_NHAT.value}.aspx'
        query_params = {
            'ItemID': vbpl_id
        }
        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                if vbpl_type == VbplType.PHAP_QUY:
                    doc_map_title_nodes = soup.find_all('div', {'class': re.compile('title')})
                    for doc_map_title_node in doc_map_title_nodes:
                        doc_map_title = get_html_node_text(doc_map_title_node)

                        doc_map_content_node = doc_map_title_node.find_next_sibling('div')
                        doc_map_list = doc_map_content_node.find_all('li')
                        for doc_map in doc_map_list:
                            link = doc_map.find('a')
                            link_ref = re.findall(find_id_regex, link.get('href'))
                            doc_map_id = None

                            if len(link_ref) > 0:
                                doc_map_id = int(link_ref[0])
                            else:
                                doc_title = link.text.strip()

                                search_resp = await cls.call(method='GET',
                                                             url_path=f'/VBQPPL_UserControls/Publishing_22/TimKiem/p_{vbpl_type.value}.aspx?IsVietNamese=True',
                                                             query_params=convert_dict_to_pascal({
                                                                 'row_per_page': cls._default_row_per_page,
                                                                 'page': 1,
                                                                 'keyword': doc_title
                                                             }))
                                if search_resp.status == HTTPStatus.OK:
                                    search_soup = BeautifulSoup(await search_resp.text(), 'lxml')
                                    titles = search_soup.find_all('p', {"class": "title"})
                                    if len(titles) > 0:
                                        search_link = titles[0].find('a')
                                        doc_map_id = int(re.findall(find_id_regex, search_link.get('href'))[0])

                            new_vbpl_doc_map = VbplDocMap(
                                source_id=vbpl_id,
                                doc_map_id=doc_map_id,
                                doc_map_type=doc_map_title
                            )
                            with LocalSession.begin() as session:
                                check_doc_map = session.query(VbplDocMap).filter(
                                    VbplDocMap.source_id == new_vbpl_doc_map.source_id,
                                    VbplDocMap.doc_map_id == new_vbpl_doc_map.doc_map_id).first()
                                if check_doc_map is None:
                                    session.add(new_vbpl_doc_map)

                elif vbpl_type == VbplType.HOP_NHAT:
                    doc_map_nodes = soup.find_all('div', {'class': 'w'})
                    if len(doc_map_nodes) > 1:
                        doc_map_nodes = doc_map_nodes[:-1]
                    else:
                        return
                    for doc_map_node in doc_map_nodes:
                        link = doc_map_node.find('a')
                        link_ref = re.findall(find_id_regex, link.get('href'))
                        doc_map_id = int(link_ref[0])

                        new_vbpl_doc_map = VbplDocMap(
                            source_id=vbpl_id,
                            doc_map_id=doc_map_id,
                            doc_map_type='Văn bản được hợp nhất'
                        )
                        with LocalSession.begin() as session:
                            session.add(new_vbpl_doc_map)
            sleep(1)
        except Exception as e:
            _logger.exception(f'Crawl vbpl doc map {vbpl_id} {e}')
            raise CommonException(500, 'Crawl vbpl luoc do')

    @classmethod
    async def search_concetti(cls, vbpl: Vbpl):
        search_url = f'/documents/search'
        key_type = ['title', 'sub_title', 'serial_number']
        select_params = ('active,'
                         'slug,'
                         'key,'
                         'name,'
                         'number,'
                         'type%7B%7D,'
                         'branches%7B%7D,'
                         'issuingAgency%7B%7D,'
                         'issueDate,'
                         'effectiveDate,'
                         'expiryDate,'
                         'gazetteNumber,'
                         'gazetteDate,'
                         'createdAt')
        date_format = '%Y-%m-%d'
        max_page = 2
        threshold = 0.8
        found = False
        query_params = {
            'target': 'document',
            'sort': 'keyword',
            'limit': 5,
            'select': select_params
        }
        if vbpl.issuance_date is not None:
            query_params['issueDateFrom'] = convert_datetime_to_str(vbpl.issuance_date)
        if vbpl.effective_date is not None:
            query_params['effectiveDateFrom'] = convert_datetime_to_str(vbpl.effective_date)
        if vbpl.expiration_date is not None:
            query_params['expiryDateFrom'] = convert_datetime_to_str(vbpl.expiration_date)

        for key in key_type:
            if found:
                break
            search_key = getattr(vbpl, key)
            if search_key is None:
                continue
            query_params['key'] = quote(search_key)
            for i in range(max_page):
                if found:
                    break
                query_params['page'] = i + 1
                params = concetti_query_params_url_encode(query_params)
                try:
                    async with aiohttp.ClientSession(trust_env=True) as session:
                        async with session.request('GET',
                                                   yarl.URL(f'{cls._concetti_base_url + search_url}?{params}',
                                                            encoded=True),
                                                   headers=cls.get_headers()
                                                   ) as resp:
                            await resp.text()
                    if resp.status == HTTPStatus.OK:
                        raw_json = await resp.json()
                        result_items = raw_json['items']

                        if len(result_items) == 0:
                            continue

                        for item in result_items:
                            if (Levenshtein.ratio(search_key, item['name']) >= threshold
                                    or Levenshtein.ratio(search_key, item['number']) >= threshold
                                    or Levenshtein.ratio(search_key, item['key']) >= threshold):

                                # Update effective date, expiry date and state of vbpl
                                effective_date_str = item['effectiveDate']
                                expiry_date_str = item['expiryDate']
                                if effective_date_str is not None:
                                    effective_date = datetime.strptime(effective_date_str, date_format)
                                    vbpl.effective_date = effective_date
                                    if effective_date > datetime.now():
                                        vbpl.state = 'Chưa có hiệu lực'
                                    else:
                                        if expiry_date_str is None:
                                            vbpl.state = 'Có hiệu lực'
                                        else:
                                            expiry_date = datetime.strptime(expiry_date_str, date_format)
                                            vbpl.expiration_date = expiry_date
                                            if expiry_date < datetime.now():
                                                vbpl.state = 'Hết hiệu lực'
                                            else:
                                                vbpl.state = 'Có hiệu lực'

                                # get vbpl sector
                                branches = item['branches']
                                branches_names = []
                                for branch in branches:
                                    branches_names.append(branch['name'])
                                if len(branches_names) > 0:
                                    vbpl.sector = ' - '.join(branches_names)

                                # fetch pdf if needed
                                if vbpl.org_pdf_link is None or vbpl.org_pdf_link.strip() == '':
                                    slug = item['slug']
                                    doc_url = '/documents/slug'
                                    try:
                                        async with aiohttp.ClientSession(trust_env=True) as session:
                                            async with session.request('GET',
                                                                       f'{cls._concetti_base_url + doc_url}/{slug}',
                                                                       headers=cls.get_headers()
                                                                       ) as doc_resp:
                                                await doc_resp.text()
                                        if resp.status == HTTPStatus.OK:
                                            raw_doc_json = await doc_resp.json()
                                            pdf_id = raw_doc_json['pdfFile']
                                            if pdf_id is not None:
                                                pdf_url = f'{cls._concetti_base_url}/files/{pdf_id}/fetch'
                                                vbpl.org_pdf_link = pdf_url
                                                vbpl.file_link = get_document(pdf_url, True, pdf_id, True)
                                    except Exception as e:
                                        _logger.exception(f'Get concetti {slug} {e}')
                                        raise CommonException(500, 'Get concetti')

                                found = True
                                break
                except Exception as e:
                    _logger.exception(f'Search using concetti {e}')
                    raise CommonException(500, 'Search using concetti')

        if vbpl.sector is None:
            vbpl.sector = 'Lĩnh vực khác'

    @classmethod
    async def additional_html_crawl(cls, vbpl: Vbpl):
        search_url = '/page/tim-van-ban.aspx'
        key_type = ['title', 'sub_title', 'serial_number']
        threshold = 0.8
        found = False
        results = []

        for key in key_type:
            if found:
                break

            if getattr(vbpl, key) is None:
                continue

            search_key = getattr(vbpl, key)
            query_params = {
                'keyword': search_key,
                'sort': 1,
            }
            try:
                async with aiohttp.ClientSession(trust_env=True) as session:
                    async with session.request('GET',
                                               cls._tvpl_base_url + search_url,
                                               params=query_params,
                                               headers=cls.get_headers()
                                               ) as resp:
                        await resp.text()
            except Exception as e:
                _logger.exception(f'Search tvpl {e}')
                raise CommonException(500, 'Search tvpl')
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                search_results = soup.find_all('p', {'class': 'nqTitle'})

                for result in search_results:
                    search_text = get_html_node_text(result)
                    if Levenshtein.ratio(search_text, search_key) >= threshold:
                        found = True
                        result_url = result.find('a').get('href')
                        try:
                            async with aiohttp.ClientSession(trust_env=True) as session:
                                async with session.request('GET',
                                                           result_url,
                                                           headers=cls.get_headers()
                                                           ) as full_text_resp:
                                    await full_text_resp.text()
                            if full_text_resp.status == HTTPStatus.OK:
                                full_text_soup = BeautifulSoup(await full_text_resp.text(), 'lxml')
                                full_text = full_text_soup.find('div', {'class': 'cldivContentDocVn'})

                                if full_text is None:
                                    return None

                                vbpl.html = str(full_text)

                                lines = full_text.find_all('p')
                                if len(lines) == 0:
                                    lines = full_text.find_all('div')
                                results = cls.process_html_full_text(vbpl, lines)
                        except Exception as e:
                            _logger.exception(f'Get tvpl html {result_url} {e}')
                            raise CommonException(500, 'Get tvpl html')
        return results

    @classmethod
    async def crawl_vbpl_by_id(cls, vbpl_id, vbpl_type: VbplType):
        new_vbpl = Vbpl(
            id=vbpl_id,
        )
        if vbpl_type == VbplType.HOP_NHAT:
            await cls.crawl_vbpl_hopnhat_info(new_vbpl)
            await cls.search_concetti(new_vbpl)
            await cls.crawl_vbpl_hopnhat_fulltext(new_vbpl)
            with LocalSession.begin() as session:
                session.add(new_vbpl)
        else:
            await cls.crawl_vbpl_phapquy_info(new_vbpl)
            await cls.search_concetti(new_vbpl)
            vbpl_fulltext = await cls.crawl_vbpl_phapquy_fulltext(new_vbpl)
            with LocalSession.begin() as session:
                session.add(new_vbpl)
                if vbpl_fulltext is not None:
                    for fulltext_record in vbpl_fulltext:
                        session.add(fulltext_record)

    @classmethod
    async def fetch_vbpl_by_id(cls, vbpl_id):
        with LocalSession.begin() as session:
            target_vbpl = session.query(Vbpl, VbplDocMap, VbplToanVan). \
                join(VbplDocMap, Vbpl.id == VbplDocMap.source_id). \
                join(VbplToanVan, VbplDocMap.source_id == VbplToanVan.vbpl_id). \
                where(Vbpl.id == vbpl_id).order_by(Vbpl.updated_at.desc())

            if target_vbpl.effective_date < datetime.now() and target_vbpl.state == "Chưa có hiệu lực":
                target_vbpl.state = "Có hiệu lực"
                values_to_update = {
                    Vbpl.state: "Có hiệu lực"
                }
                update_statement = update(Vbpl).where(Vbpl.id == vbpl_id).values(values_to_update)
                session.execute(update_statement)

        print(target_vbpl)
        return target_vbpl
