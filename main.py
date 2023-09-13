from bs4 import BeautifulSoup, PageElement
import requests
import re

test_request = requests.get('https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=32801')
# print(test_request.text)
soup = BeautifulSoup(test_request.text, 'lxml')
fulltext = soup.find('div', {"class": "toanvancontent"})

find_id_regex = '(?<=ItemID=).*?(?=&)'
find_section_regex = '>((Điều)|(Điều thứ))'
find_chapter_regex = '>Chương'
find_part_regex = '>Mục'
find_mini_part_regex = '>Tiểu mục'

lines = fulltext.find_all('p')

current_chapter_number = None
current_chapter_name = None
current_part_number = None
current_part_name = None
current_mini_part_number = None
current_mini_part_name = None

for line in lines:
    if re.search(find_section_regex, str(line)):
        section_number = int(re.findall('(?<=Điều )\\d+', line.text)[0])
        # section_name = re.findall('(?<=Điều \\d+)\\w+', line.text)[0]

        next_node = line
        while True:
            next_node = next_node.find_next_sibling('p')

            if next_node is None:
                break

            if re.search(find_chapter_regex, str(next_node)):
                current_chapter_number = int(re.findall('(?<=Chương )\\d+', next_node.text)[0])
                next_node = next_node.find_next_sibling('p')
                current_chapter_name = next_node.text
                continue

            if re.search(find_part_regex, str(next_node)):
                current_part_number = int(re.findall('(?<=Mục )\\d+', next_node.text)[0])
                next_node = next_node.find_next_sibling('p')
                current_part_name = next_node.text
                continue

            if re.search(find_mini_part_regex, str(next_node)):
                current_mini_part_number = int(re.findall('(?<=Tiểu mục )\\d+', next_node.text)[0])
                next_node = next_node.find_next_sibling('p')
                current_mini_part_name = next_node.text
                continue

            if re.search(find_section_regex, str(next_node)):
                break
            print(next_node.text)
