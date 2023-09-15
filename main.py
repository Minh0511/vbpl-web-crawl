from bs4 import BeautifulSoup, PageElement
import requests
import re

from app.service.vbpl import VbplService

test_request = requests.get('https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=96172')
# print(test_request.text)
soup = BeautifulSoup(test_request.text, 'lxml')
fulltext = soup.find('div', {"class": "toanvancontent"})

# find_id_regex = '(?<=ItemID=).*?(?=&)'

vbpl_service = VbplService()
vbpl_service.crawl_vbpl_toanvan(96172)
