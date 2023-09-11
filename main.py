from bs4 import BeautifulSoup
import requests
import re

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
