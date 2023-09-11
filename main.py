from bs4 import BeautifulSoup
import requests
import re
# import os

# from app.pdf.get_pdf import get_pdf

test_request = requests.get('https://vbpl.vn/VBQPPL_UserControls/Publishing_22/TimKiem/p_KetQuaTimKiemVanBan.aspx?IsVietNamese=True&Page=2&RowPerPage=10')
# print(test_request.text)
soup = BeautifulSoup(test_request.text, 'lxml')
titles = soup.find_all('p', {"class": "title"})

find_id_regex = '(?<=ItemID=).*?(?=&)'

for title in titles:
    link = title.find('a')
    print(re.findall(find_id_regex, link.get('href'))[0])

# message = soup.find('div', {'class': 'message'})
# print(message.find('strong').string)

# urls = ["https://bientap.vbpl.vn//FileData/TW/Lists/vbpq/Attachments/32801/VanBanGoc_Hien%20phap%202013.pdf",
#         "https://bientap.vbpl.vn//FileData/TW/Lists/vbpq/Attachments/139264/VanBanGoc_BO%20LUAT%2045%20QH14.pdf"]
# store_folder = 'vbpl_pdf'
# os.makedirs(store_folder, exist_ok=True)
# for pdf_url in urls:
#     get_pdf(pdf_url, store_folder)
