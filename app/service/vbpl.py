import logging
import math
import re
import copy
from datetime import datetime
from http import HTTPStatus
from typing import Dict

import aiohttp
import yarl

from app.entity.vbpl import VbplFullTextField
from app.helper.custom_exception import CommonException
from app.helper.enum import VbplTab, VbplType
from app.model import VbplToanVan, Vbpl, VbplRelatedDocument, VbplDocMap
from app.service.get_pdf import get_document
from setting import setting
from app.helper.utility import convert_dict_to_pascal, get_html_node_text, convert_datetime_to_str, \
    concetti_query_params_url_encode
from app.helper.db import LocalSession
from urllib.parse import quote
import Levenshtein
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)
find_id_regex = '(?<=ItemID=)\\d+'


class VbplService:
    _api_base_url = setting.VBPl_BASE_URL
    _default_row_per_page = 10
    _find_big_part_regex = '>((Phần)|(Phần thứ))'
    _find_section_regex = '>((Điều)|(Điều thứ))'
    _find_chapter_regex = '^Chương [IVX]+'
    _find_part_regex = '^Mục [IVX]+'
    _find_part_regex_2 = '^Mu.c [IVX]+'
    _find_mini_part_regex = '^Tiểu mục [IVX]+'
    _empty_related_doc_msg = 'Nội dung đang cập nhật'
    _concetti_base_url = setting.CONCETTI_BASE_URL

    @classmethod
    def get_headers(cls) -> Dict:
        return {'Content-Type': 'application/json'}

    @classmethod
    async def call(cls, method: str, url_path: str, query_params=None, json_data=None, timeout=30):
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
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Get total doc')
        if resp.status == HTTPStatus.OK:
            soup = BeautifulSoup(await resp.text(), 'lxml')
            message = soup.find('div', {'class': 'message'})
            return int(message.find('strong').string)

    @classmethod
    async def crawl_all_vbpl(cls, vbpl_type: VbplType):
        total_doc = await cls.get_total_doc(vbpl_type)
        total_pages = math.ceil(total_doc / cls._default_row_per_page)
        prev_id_set = set()
        full_id_list = []
        progress = 0

        for i in range(total_pages):
            if i == 1:
                break
            query_params = convert_dict_to_pascal({
                'row_per_page': cls._default_row_per_page,
                'page': i + 1
            })

            try:
                resp = await cls.call(method='GET',
                                      url_path=f'/VBQPPL_UserControls/Publishing_22/TimKiem/p_{vbpl_type.value}.aspx?IsVietNamese=True',
                                      query_params=query_params)
            except Exception as e:
                _logger.exception(e)
                raise CommonException(500, 'Crawl all doc')
            if resp.status == HTTPStatus.OK:
                soup = BeautifulSoup(await resp.text(), 'lxml')
                titles = soup.find_all('p', {"class": "title"})
                sub_titles = soup.find_all('div', {'class': "des"})
                check_last_page = False
                id_set = set()

                for j in range(len(titles)):
                    title = titles[j]
                    sub_title = sub_titles[j]

                    link = title.find('a')
                    doc_id = int(re.findall(find_id_regex, link.get('href'))[0])
                    if doc_id in prev_id_set:
                        check_last_page = True
                        break
                    id_set.add(doc_id)
                    full_id_list.append(doc_id)

                    with LocalSession.begin() as session:
                        statement = session.query(Vbpl).filter(Vbpl.id == doc_id)
                        check_vbpl = session.execute(statement).all()
                        if len(check_vbpl) != 0:
                            progress += 1
                            print(f"Progress: {progress}/{cls._default_row_per_page * 1000}")
                            continue

                    new_vbpl = Vbpl(
                        id=doc_id,
                        title=get_html_node_text(link),
                        sub_title=get_html_node_text(sub_title)
                    )
                    if vbpl_type == VbplType.PHAP_QUY:
                        await cls.crawl_vbpl_phapquy_info(new_vbpl)
                        await cls.search_concetti(new_vbpl)
                        vbpl_fulltext = await cls.crawl_vbpl_phapquy_fulltext(new_vbpl)

                        with LocalSession.begin() as session:
                            session.add(new_vbpl)
                            if vbpl_fulltext is not None:
                                for fulltext_record in vbpl_fulltext:
                                    session.add(fulltext_record)

                    elif vbpl_type == VbplType.HOP_NHAT:
                        await cls.crawl_vbpl_hopnhat_info(new_vbpl)
                        await cls.search_concetti(new_vbpl)
                        await cls.crawl_vbpl_hopnhat_fulltext(new_vbpl)

                        with LocalSession.begin() as session:
                            session.add(new_vbpl)

                    # update progress
                    progress += 1
                    print(f"Progress: {progress}/{cls._default_row_per_page * 1000}")

                if check_last_page:
                    break

                prev_id_set = id_set

        for doc_id in full_id_list:
            await cls.crawl_vbpl_related_doc(doc_id)
            await cls.crawl_vbpl_doc_map(doc_id, vbpl_type)

    @classmethod
    def update_vbpl_phapquy_fulltext(cls, line, fulltext_obj: VbplFullTextField):
        line_content = get_html_node_text(line)
        check = False

        if re.search(cls._find_big_part_regex, str(line)):
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
    async def crawl_vbpl_phapquy_fulltext(cls, vbpl: Vbpl):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.FULL_TEXT.value}.aspx'
        query_params = {
            'ItemID': vbpl.id
        }
        results = []

        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Crawl vbpl toan van')

        if resp.status == HTTPStatus.OK:
            soup = BeautifulSoup(await resp.text(), 'lxml')
            fulltext = soup.find('div', {"class": "toanvancontent"})

            if fulltext is None:
                return None

            vbpl.html = str(fulltext)

            lines = fulltext.find_all('p')
            vbpl_fulltext_obj = VbplFullTextField()

            for line in lines:
                if re.search(cls._find_section_regex, str(line)):
                    break

                vbpl_fulltext_obj, check = cls.update_vbpl_phapquy_fulltext(line, vbpl_fulltext_obj)
                if check:
                    continue

            for line in lines:
                if re.search(cls._find_section_regex, str(line)):

                    line_content = get_html_node_text(line)
                    section_number_search = re.search('\\b\\d+', line_content)
                    section_number = int(section_number_search.group())

                    section_name = line_content[section_number_search.span()[1]:]
                    section_name_refined = None
                    section_name_search = re.search('\\b\\w', section_name)
                    if section_name_search:
                        section_name_refined = section_name[section_name_search.span()[0]:]

                    current_fulltext_config = copy.deepcopy(vbpl_fulltext_obj)
                    content = []

                    next_node = line
                    while True:
                        next_node = next_node.find_next_sibling('p')

                        if next_node is None:
                            break

                        vbpl_fulltext_obj, check = cls.update_vbpl_phapquy_fulltext(next_node, vbpl_fulltext_obj)
                        if check:
                            next_node = next_node.find_next_sibling('p')
                            continue

                        if re.search(cls._find_section_regex, str(next_node)) or re.search('_{2,}', str(next_node)):
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
    async def crawl_vbpl_hopnhat_fulltext(cls, vbpl: Vbpl):
        if vbpl.org_pdf_link is not None and vbpl.org_pdf_link.strip() != '':
            return

        aspx_url = f'/TW/Pages/vbpq-{VbplTab.FULL_TEXT_HOP_NHAT.value}.aspx'
        query_params = {
            'ItemID': vbpl.id
        }

        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Crawl vbpl hop nhat toan van')
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

                try:
                    resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
                except Exception as e:
                    _logger.exception(e)
                    raise CommonException(500, 'Crawl vbpl hop nhat toan van')
                if resp.status == HTTPStatus.OK:
                    soup = BeautifulSoup(await resp.text(), 'lxml')
                    vbpl_view = soup.find('div', {'class': 'vbProperties'})
                    pdf_view_object = vbpl_view.find('object')
                    if pdf_view_object is not None:
                        pdf_link = re.findall('.+.pdf', pdf_view_object.get('data'))[0]
                        vbpl.org_pdf_link = setting.VBPL_PDF_BASE_URL + pdf_link
                        vbpl.file_link = get_document(vbpl.org_pdf_link, True)

    @classmethod
    async def crawl_vbpl_hopnhat_info(cls, vbpl: Vbpl):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.ATTRIBUTE_HOP_NHAT.value}.aspx'
        query_params = {
            'ItemID': vbpl.id
        }

        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Crawl vbpl thuoc tinh')
        if resp.status == HTTPStatus.OK:
            soup = BeautifulSoup(await resp.text(), 'lxml')

            properties = soup.find('div', {"class": "vbProperties"})
            files = soup.find('ul', {'class': 'fileAttack'})

            bread_crumbs = soup.find('div', {"class": "box-map"})
            title = bread_crumbs.find('a', {"href": ""})
            vbpl.title = title.text.strip()
            sub_title = soup.find('td', {'class': 'title'})
            vbpl.sub_title = sub_title.text.strip()

            table_rows = properties.find_all('tr')
            date_format = '%d/%m/%Y'

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
                        if field == 'effective_date':
                            field_value = datetime.strptime(get_html_node_text(field_value_node), date_format)
                            if field_value < datetime.now():
                                vbpl.state = "Có hiệu lực"
                        if field == 'effective_date' or field == 'gazette_date':
                            try:
                                field_value = datetime.strptime(get_html_node_text(field_value_node), date_format)
                                print(field_value)
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
                    local_links.append(get_document(url, True))
                vbpl.file_link = ' '.join(local_links)
                vbpl.org_pdf_link = ' '.join(file_urls)

    @classmethod
    async def crawl_vbpl_phapquy_info(cls, vbpl: Vbpl):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.ATTRIBUTE.value}.aspx'
        query_params = {
            'ItemID': vbpl.id
        }

        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Crawl vbpl thuoc tinh')
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
                        if field == 'effective_date':
                            field_value = datetime.strptime(get_html_node_text(field_value_node), date_format)
                            if field_value < datetime.now():
                                vbpl.state = "Có hiệu lực"
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
                if re.search('.+.pdf', get_html_node_text(link_node)) \
                        or re.search('.+.doc', get_html_node_text(link_node)) \
                        or re.search('.+.docx', get_html_node_text(link_node)):
                    href = link_node['href']
                    file_url = href[len('javascript:downloadfile('):-2].split(',')[1][1:-1]
                    file_urls.append(quote(setting.VBPL_PDF_BASE_URL + file_url, safe='/:?'))

            if len(file_urls) > 0:
                local_links = []
                for url in file_urls:
                    local_links.append(get_document(url, True))
                vbpl.file_link = ' '.join(local_links)
                vbpl.org_pdf_link = ' '.join(file_urls)

    @classmethod
    async def crawl_vbpl_related_doc(cls, vbpl_id):
        aspx_url = f'/TW/Pages/vbpq-{VbplTab.RELATED_DOC.value}.aspx'
        query_params = {
            'ItemID': vbpl_id
        }
        try:
            resp = await cls.call(method='GET', url_path=aspx_url, query_params=query_params)
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Crawl vbpl van ban lien quan')
        if resp.status == HTTPStatus.OK:
            soup = BeautifulSoup(await resp.text(), 'lxml')

            related_doc_node = soup.find('div', {'class': 'vbLienQuan'})
            if related_doc_node is None or re.search(cls._empty_related_doc_msg, get_html_node_text(related_doc_node)):
                # print("No related doc")
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
                        session.add(new_vbpl_related_doc)
                    # print(new_vbpl_related_doc)

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
        except Exception as e:
            _logger.exception(e)
            raise CommonException(500, 'Crawl vbpl luoc do')
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
                            try:
                                search_resp = await cls.call(method='GET',
                                                             url_path=f'/VBQPPL_UserControls/Publishing_22/TimKiem/p_{vbpl_type.value}.aspx?IsVietNamese=True',
                                                             query_params=convert_dict_to_pascal({
                                                                 'row_per_page': cls._default_row_per_page,
                                                                 'page': 1,
                                                                 'keyword': doc_title
                                                             }))
                            except Exception as e:
                                _logger.exception(e)
                                raise CommonException(500, 'Crawl vbpl luoc do')
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
                            session.add(new_vbpl_doc_map)
                        # print(new_vbpl_doc_map)

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
                    # print(new_vbpl_doc_map)

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
                except Exception as e:
                    _logger.exception(e)
                    raise CommonException(500, 'Search using concetti')
                if resp.status == HTTPStatus.OK:
                    raw_json = await resp.json()
                    result_items = raw_json['items']
                    # print("Result", result_items)
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

                            found = True
                            break

        if vbpl.sector is None:
            vbpl.sector = 'Lĩnh vực khác'

    @classmethod
    async def crawl_vbpl_by_id(cls, vbpl_id, vbpl_type: VbplType):
        new_vbpl = Vbpl(
            id=vbpl_id,
        )
        await cls.crawl_vbpl_phapquy_info(new_vbpl)
        await cls.search_concetti(new_vbpl)
        vbpl_fulltext = await cls.crawl_vbpl_phapquy_fulltext(new_vbpl)
        if vbpl_type == VbplType.HOP_NHAT:
            await cls.crawl_vbpl_hopnhat_info(new_vbpl)
            await cls.search_concetti(new_vbpl)
            await cls.crawl_vbpl_hopnhat_fulltext(new_vbpl)
            with LocalSession.begin() as session:
                session.add(new_vbpl)
        else:
            with LocalSession.begin() as session:
                session.add(new_vbpl)
                if vbpl_fulltext is not None:
                    for fulltext_record in vbpl_fulltext:
                        session.add(fulltext_record)
