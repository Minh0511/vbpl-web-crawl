import asyncio
import time

from app.helper.enum import VbplType
from app.model import Vbpl
from app.service.anle import AnleService

from app.service.vbpl import VbplService

vbpl_service = VbplService()
anle_service = AnleService()

while True:
    try:
        asyncio.run(anle_service.crawl_all_anle())
        asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.PHAP_QUY))
        asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.HOP_NHAT))
    except Exception as e:
        continue
    time.sleep(15)
