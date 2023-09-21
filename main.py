import asyncio
import glob
import os
from urllib.parse import quote, urlencode

from bs4 import BeautifulSoup, PageElement
import requests
import re

from app.helper.db import LocalSession
from app.helper.enum import VbplType
from app.model import Vbpl, Anle
from app.service.anle import AnleService
# import os

# from app.pdf.get_pdf import get_pdf

from app.service.vbpl import VbplService

vbpl_service = VbplService()
anle_service = AnleService()

asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.PHAP_QUY))

# test_vbpl = Vbpl(
#     id=32801,
#     title='Luật 31/VBHN-VPQH',
#     sub_title='hợp nhất Luật Xử lý vi phạm hành chính',
# )
#
# asyncio.run(vbpl_service.crawl_vbpl_phapquy_info(test_vbpl))
# asyncio.run(vbpl_service.search_concetti(test_vbpl))
# asyncio.run(vbpl_service.crawl_vbpl_phapquy_fulltext(test_vbpl))
#
# asyncio.run(vbpl_service.crawl_vbpl_hopnhat_info(test_vbpl))
# asyncio.run(vbpl_service.search_concetti(test_vbpl))
# asyncio.run(vbpl_service.crawl_vbpl_hopnhat_fulltext(test_vbpl))

# print(test_vbpl)
# asyncio.run(anle_service.crawl_all_anle())
