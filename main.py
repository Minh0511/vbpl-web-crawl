import asyncio
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

# vbpl_service = VbplService()
anle_service = AnleService()

# test_anle = Anle(doc_id='TAND292159')
# asyncio.run(anle_service.crawl_anle_info(test_anle))
asyncio.run(anle_service.crawl_all_anle())
