import asyncio
import os
import sys
import time

from app.helper.enum import VbplType
from app.model import Anle, Vbpl
from app.service.anle import AnleService

from app.service.vbpl import VbplService

vbpl_service = VbplService()
anle_service = AnleService()


# asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.PHAP_QUY))

# Import your functions here
# Replace 'crawl_function_1', 'crawl_function_2', and 'function_with_parameter' with your actual function names

def crawl_all_vbpl_phap_quy():
    # Implement your first crawling function here
    print("Đang cào dữ liệu vbpl - văn bản pháp quy")
    asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.PHAP_QUY))
    print("Cào dữ liệu hoàn tất")


def crawl_all_vbpl_hop_nhat():
    # Implement your second crawling function here
    print("Đang cào dữ liệu vbpl - văn bản hợp nhất")
    asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.HOP_NHAT))
    print("Cào dữ liệu hoàn tất")


def craw_all_anle():
    # Implement your third function that requires an ID parameter here
    print("Đang cào dữ liệu án lệ")
    asyncio.run(anle_service.crawl_all_anle())
    print("Cào dữ liệu hoàn tất")


def crawl_anle_by_id(id):
    print(f"Đang cào dữ liệu của án lệ có id: {id}")
    new_anle = Anle(doc_id=id)
    asyncio.run(anle_service.crawl_anle_info(new_anle))
    print("Cào dữ liệu hoàn tất")


def crawl_vbpl_by_id(id):
    print(f"Đang cào dữ liệu của vbpl có id: {id}")
    asyncio.run(vbpl_service.crawl_vbpl_by_id(id))
    print("Cào dữ liệu hoàn tất")


def print_menu():
    menu = """
╔══════════════════════════════════════════════════════╗
║             Cào dữ liệu vbpl - án lệ                 ║
╟──────────────────────────────────────────────────────╢
║ Nhập các lựa chọn sau và ấn enter để chạy chương     ║ 
║ trình cào dữ liệu, ví dụ: nhập 3 và ấn enter sẽ chạy ║
║ chương trình cào toàn bộ dữ liệu án lê.              ║ 
║------------------------------------------------------║ 
║ 1. Cào dữ liệu vbpl - văn bản pháp quy               ║
║ 2. Cào dữ liệu vbpl - văn bản hợp nhất               ║
║ 3. Cào toàn bộ dữ liệu án lệ                         ║
║ 4. Cào văn bản pháp luật bằng ID                     ║
║ 5. Cào án lệ bằng ID                                 ║
║ 6. --help                                            ║
║ 7. Thoát                                             ║
╚══════════════════════════════════════════════════════╝
"""
    print(menu)


def main():
    print_menu()  # Print the menu initially
    try:
        while True:
            choice = input("Nhập lựa chọn: ")

            if choice == "1":
                crawl_all_vbpl_phap_quy()
            elif choice == "2":
                crawl_all_vbpl_hop_nhat()
            elif choice == "3":
                craw_all_anle()
            elif choice == "4":
                vbpl_id = input("Nhập ID văn bản: ")
                crawl_vbpl_by_id(vbpl_id)
            elif choice == "5":
                anle_id = input("Nhập ID án lệ: ")
                crawl_anle_by_id(anle_id)
            elif choice == "7":
                print("Đang thoát chương trình.")
                break
            elif choice == "6" or choice == "--help":
                print_menu()  # Display the menu again
            else:
                print("Yêu cầu không hợp lệ, để biết các câu lệnh cần dùng, nhập 6 hoặc --help.")
    except KeyboardInterrupt:
        print("\nForcefully exiting the CLI.")
        sys.exit(0)


if __name__ == "__main__":
    main()
