import asyncio
import sys

from app.helper.enum import VbplType
from app.model import Anle, Vbpl
from app.service.anle import AnleService

from app.service.vbpl import VbplService

vbpl_service = VbplService()
anle_service = AnleService()


def crawl_all_vbpl_phap_quy():
    print("Đang cào dữ liệu vbpl - văn bản pháp quy")
    asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.PHAP_QUY))
    print("Cào dữ liệu hoàn tất")


def crawl_all_vbpl_hop_nhat():
    print("Đang cào dữ liệu vbpl - văn bản hợp nhất")
    asyncio.run(vbpl_service.crawl_all_vbpl(VbplType.HOP_NHAT))
    print("Cào dữ liệu hoàn tất")


def craw_all_anle():
    print("Đang cào dữ liệu án lệ")
    asyncio.run(anle_service.crawl_all_anle())
    print("Cào dữ liệu hoàn tất")


def crawl_anle_by_id(id):
    print(f"Đang cào dữ liệu của án lệ có id: {id}")
    new_anle = Anle(doc_id=id)
    asyncio.run(anle_service.crawl_anle_info(new_anle))
    print("Cào dữ liệu hoàn tất")


def crawl_vbpl_by_id_phap_quy(id):
    print(f"Đang cào dữ liệu của văn bản pháp quy có id: {id}")
    asyncio.run(vbpl_service.crawl_vbpl_by_id(id, VbplType.PHAP_QUY))
    print("Cào dữ liệu hoàn tất")


def crawl_vbpl_by_id_hop_nhat(id):
    print(f"Đang cào dữ liệu của văn bản hợp nhất có id: {id}")
    asyncio.run(vbpl_service.crawl_vbpl_by_id(id, VbplType.HOP_NHAT))
    print("Cào dữ liệu hoàn tất")


def fetch_vbpl_by_id(id):
    print(f"Đang lấy dữ liệu của văn bản pháp luật có id: {id}")
    asyncio.run(vbpl_service.fetch_vbpl_by_id(id))
    print("Lấy dữ liệu hoàn tất")


def fetch_anle_by_id(id):
    print(f"Đang lấy dữ liệu của án lệ có id: {id}")
    asyncio.run(anle_service.fetch_anle_by_id(id))
    print("Lấy dữ liệu hoàn tất")


def preview_vbpl(num_of_rows, issuance_date):
    print(f"Đang tải bản xem trước của {num_of_rows} vbpl")
    asyncio.run(vbpl_service.get_vbpl_preview(num_of_rows, issuance_date))
    print("Bản xem trước được lưu tại documents/preview/vbpl")


def preview_anle():
    print(f"Đang tải bản xem trước của án lệ")
    asyncio.run(anle_service.get_anle_preview())
    print("Bản xem trước được lưu tại documents/preview/anle")


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
║ 4. Cào văn bản pháp quy bằng ID                      ║
║ 5. Cào văn bản hợp nhất bằng ID                      ║
║ 6. Cào án lệ bằng ID                                 ║
║ 7. Tìm vbpl theo ID                                  ║
║ 8. Tìm án lệ theo ID                                 ║
║ 9. Preview án lệ                                     ║
║ 10. Preview văn bản pháp luật                        ║
║ 11. --help                                           ║
║ 12. Thoát                                            ║
╚══════════════════════════════════════════════════════╝
"""
    print(menu)


def main():
    print_menu()
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
                vbpl_id = input("Nhập ID văn bản pháp quy (VD: 32801): ")
                crawl_vbpl_by_id_phap_quy(vbpl_id)
            elif choice == "5":
                vbpl_id = input("Nhập ID văn bản hợp nhất (VD: 147301): ")
                crawl_vbpl_by_id_hop_nhat(vbpl_id)
            elif choice == "6":
                anle_id = input("Nhập ID án lệ (VD: TAND292162): ")
                crawl_anle_by_id(anle_id)
            elif choice == "7":
                vbpl_id = input("Nhập ID vbpl (VD: 32801): ")
                fetch_vbpl_by_id(vbpl_id)
            elif choice == "8":
                anle_id = input("Nhập ID án lệ (VD: TAND292162): ")
                fetch_anle_by_id(anle_id)
            elif choice == "9":
                preview_anle()
            elif choice == "10":
                num_of_rows = input("Nhập số dòng (VD: 3): ")
                issuance_date = input("Nhập ngày ban hành (DD/MM/YYYY): ")
                preview_vbpl(num_of_rows, issuance_date)
            elif choice == "11" or choice == "--help":
                print_menu()
            elif choice == "12":
                print("Đang thoát chương trình.")
                break
            else:
                print("Yêu cầu không hợp lệ, để biết các câu lệnh cần dùng, nhập 6 hoặc --help.")
    except KeyboardInterrupt:
        print("\nForcefully exiting the CLI.")
        sys.exit(0)


if __name__ == "__main__":
    main()
