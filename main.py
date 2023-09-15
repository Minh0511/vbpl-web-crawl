import glob
import os

from bs4 import BeautifulSoup, PageElement
import requests
import re

from app.anle.process_anle_pdf import process_anle
# import os

# from app.pdf.get_pdf import get_pdf

from app.service.vbpl import VbplService

# test_request = requests.get('https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=96172')
# print(test_request.text)
# soup = BeautifulSoup(test_request.text, 'lxml')
# fulltext = soup.find('div', {"class": "toanvancontent"})

# find_id_regex = '(?<=ItemID=).*?(?=&)'

# vbpl_service = VbplService()
# vbpl_service.crawl_vbpl_toanvan(96172)

# message = soup.find('div', {'class': 'message'})
# print(message.find('strong').string)

# urls = ["https://bientap.vbpl.vn//FileData/TW/Lists/vbpq/Attachments/32801/VanBanGoc_Hien%20phap%202013.pdf",
#         "https://bientap.vbpl.vn//FileData/TW/Lists/vbpq/Attachments/139264/VanBanGoc_BO%20LUAT%2045%20QH14.pdf"]
# store_folder = 'vbpl_pdf'
# os.makedirs(store_folder, exist_ok=True)
# for pdf_url in urls:
#     get_pdf(pdf_url, store_folder)

folder_path = 'pdf/anle_pdf'
anle_files = glob.glob(os.path.join(folder_path, "*.pdf"))
for file_path in anle_files:
    file_id, anle_context, anle_solution, anle_content = process_anle(file_path)
    print(file_id)
    print('\n')
    print(anle_context)
    print('\n')
    print(anle_solution)
    print('\n')
    print(anle_content)
