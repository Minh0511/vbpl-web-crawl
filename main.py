import glob
import os

from bs4 import BeautifulSoup, PageElement
import requests
import re

from app.helper.enum import VbplType
from app.model import Vbpl, Anle
from app.service.anle import AnleService
# import os

# from app.pdf.get_pdf import get_pdf

from app.service.vbpl import VbplService

# test_request = requests.get('https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=96172')
# print(test_request.text)
# soup = BeautifulSoup(test_request.text, 'lxml')
# fulltext = soup.find('div', {"class": "toanvancontent"})

# find_id_regex = '(?<=ItemID=).*?(?=&)'

# vbpl_service = VbplService()
anle_service = AnleService()
test_vbpl = Vbpl(id=147301)
test_anle = Anle(doc_id='TAND292162')

# vbpl_service.crawl_vbpl_related_doc(test_vbpl)
# vbpl_service.crawl_vbpl_all(VbplType.PHAP_QUY)
# vbpl_service.crawl_vbpl_doc_map(test_vbpl, VbplType.HOP_NHAT)

anle_service.crawl_anle_info(test_anle)

# message = soup.find('div', {'class': 'message'})
# print(message.find('strong').string)

# urls = ["https://bientap.vbpl.vn//FileData/TW/Lists/vbpq/Attachments/32801/VanBanGoc_Hien%20phap%202013.pdf",
#         "https://bientap.vbpl.vn//FileData/TW/Lists/vbpq/Attachments/139264/VanBanGoc_BO%20LUAT%2045%20QH14.pdf"]
# store_folder = 'vbpl_pdf'
# os.makedirs(store_folder, exist_ok=True)
# for pdf_url in urls:
#     get_pdf(pdf_url, store_folder)
