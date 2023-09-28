import asyncio

from app.helper.enum import VbplType
from app.service.anle import AnleService

from app.service.vbpl import VbplService

vbpl_service = VbplService()
anle_service = AnleService()

# asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.PHAP_QUY))
asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.HOP_NHAT))

# test_vbpl = Vbpl(
#     id=96172,
#     title='Hiến pháp không số',
#     sub_title='Hiến pháp năm 2013',
# )
#
# asyncio.run(vbpl_service.crawl_vbpl_phapquy_info(test_vbpl))
# asyncio.run(vbpl_service.search_concetti(test_vbpl))
# print(asyncio.run(vbpl_service.crawl_vbpl_phapquy_fulltext(test_vbpl)))
#
# asyncio.run(vbpl_service.crawl_vbpl_hopnhat_info(test_vbpl))
# asyncio.run(vbpl_service.search_concetti(test_vbpl))
# asyncio.run(vbpl_service.crawl_vbpl_hopnhat_fulltext(test_vbpl))

# asyncio.run(vbpl_service.additional_html_crawl(test_vbpl))

# print(test_vbpl)
# asyncio.run(anle_service.crawl_all_anle())
