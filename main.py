from bs4 import BeautifulSoup, PageElement
import requests
import re

from app.service.vbpl import VbplService

test_request = requests.get('https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=96172')
# print(test_request.text)
soup = BeautifulSoup(test_request.text, 'lxml')
fulltext = soup.find('div', {"class": "toanvancontent"})

# find_id_regex = '(?<=ItemID=).*?(?=&)'
# find_big_part_regex = '>((Phần)|(Phần thứ))'
# find_section_regex = '>((Điều)|(Điều thứ))'
# find_chapter_regex = '>Chương'
# find_part_regex = '>Mục'
# find_mini_part_regex = '>Tiểu mục'
#
# lines = fulltext.find_all('p')
#
# current_big_part_number = None
# current_big_part_name = None
# current_chapter_number = None
# current_chapter_name = None
# current_part_number = None
# current_part_name = None
# current_mini_part_number = None
# current_mini_part_name = None
#
# for line in lines:
#     if re.search(find_section_regex, str(line)):
#         break
#     line_content = line.text.strip()
#
#     if re.search(find_big_part_regex, str(line)):
#         current_big_part_number_search = re.search('(?<=Phần thứ ).+', line_content)
#         current_big_part_number = line_content[current_big_part_number_search.span()[0]:]
#         next_node = line.find_next_sibling('p')
#         current_big_part_name = next_node.text.strip()
#
#         current_part_name = None
#         current_part_number = None
#         current_mini_part_name = None
#         current_mini_part_number = None
#         continue
#
#     if re.search(find_chapter_regex, str(line)):
#         current_chapter_number = re.findall('(?<=Chương ).+', line_content)[0]
#         next_node = line.find_next_sibling('p')
#         current_chapter_name = next_node.text.strip()
#
#         current_part_name = None
#         current_part_number = None
#         current_mini_part_name = None
#         current_mini_part_number = None
#         continue
#
#     if re.search(find_part_regex, str(line)):
#         current_part_number = re.findall('(?<=Mục ).+', line_content)[0]
#         next_node = line.find_next_sibling('p')
#         current_part_name = next_node.text.strip()
#         continue
#
#     if re.search(find_mini_part_regex, str(line)):
#         current_mini_part_number = re.findall('(?<=Tiểu mục ).+', line_content)[0]
#         next_node = line.find_next_sibling('p')
#         current_mini_part_name = next_node.text.strip()
#         continue
#
# for line in lines:
#     if re.search(find_section_regex, str(line)):
#         print("Mục", current_part_number, current_part_name)
#         print("Phần", current_big_part_number, current_big_part_name)
#         print("Chương", current_chapter_number, current_chapter_name)
#         print("Tiểu mục", current_mini_part_number, current_mini_part_name)
#
#         line_content = line.text.strip()
#         section_number_search = re.search('\\b\\d+', line_content)
#         section_number = int(section_number_search.group())
#         print("Điều", section_number)
#         section_name = line_content[section_number_search.span()[1]:]
#         section_name_search = re.search('\\b\\w', section_name)
#         section_name_refined = section_name[section_name_search.span()[0]:]
#         print("Tên điều", section_name_refined)
#         content = []
#
#         next_node = line
#         while True:
#             next_node = next_node.find_next_sibling('p')
#
#             if next_node is None:
#                 break
#             next_node_content = next_node.text.strip()
#
#             if re.search(find_big_part_regex, str(next_node)):
#                 current_big_part_number_search = re.search('(?<=Phần thứ ).+', next_node_content)
#                 current_big_part_number = next_node_content[current_big_part_number_search.span()[0]:]
#                 next_node = next_node.find_next_sibling('p')
#                 current_big_part_name = next_node.text.strip()
#
#                 current_part_name = None
#                 current_part_number = None
#                 current_mini_part_name = None
#                 current_mini_part_number = None
#                 continue
#
#             if re.search(find_chapter_regex, str(next_node)):
#                 current_chapter_number = re.findall('(?<=Chương ).+', next_node_content)[0]
#                 next_node = next_node.find_next_sibling('p')
#                 current_chapter_name = next_node.text.strip()
#
#                 current_part_name = None
#                 current_part_number = None
#                 current_mini_part_name = None
#                 current_mini_part_number = None
#                 continue
#
#             if re.search(find_part_regex, str(next_node)):
#                 current_part_number = re.findall('(?<=Mục ).+', next_node_content)[0]
#                 next_node = next_node.find_next_sibling('p')
#                 current_part_name = next_node.text.strip()
#                 continue
#
#             if re.search(find_mini_part_regex, str(next_node)):
#                 current_mini_part_number = re.findall('(?<=Tiểu mục ).+', next_node_content)[0]
#                 next_node = next_node.find_next_sibling('p')
#                 current_mini_part_name = next_node.text.strip()
#                 continue
#
#             if re.search(find_section_regex, str(next_node)) or re.search('_{2,}', str(next_node)):
#                 section_content = '\n'.join(content)
#                 # print(section_content)
#                 break
#
#             content.append(next_node.text.strip())

vbpl_service = VbplService()
vbpl_service.crawl_vbpl_toanvan(96172)
