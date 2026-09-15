import os
import json
import csv
import pandas as pd

# RealEstateDataProcessor: Chuyển dữ liệu JSON của từng quận sang CSV riêng/Gộp tất cả CSV thành 1 file duy nhất
class RealEstateDataProcessor:

    # Danh sách quận mặc định
    DISTRICT_NAMES = [
        '1','2','3','4','5','6','7','8','9','10',
        '11','12','binh-thanh','phu-nhuan','binh-tan',
        'go-vap','tan-binh','tan-phu','binh-chanh',
        'can-gio','cu-chi','hoc-mon','nha-be','thu-duc'
    ]

    # Format dòng CSV chuẩn
    DATA_FORMAT = {
        'id': None,
        'address': None,
        'district': None,
        'Diện tích': None,
        'Số tầng': None,
        'Số phòng ngủ': None,
        'Số phòng tắm, vệ sinh': None,
        'Mặt tiền': None,
        'Đường vào': None,
        'Hướng nhà': None,
        'Hướng ban công': None,
        'Pháp lý': None,
        'Nội thất': None,
        'Thời gian dự kiến vào ở': None,
        'Khoảng giá': None,
        'Mức giá điện': None,
        'Mức giá nước': None,
        'Mức giá internet': None,
        'Tiện ích': None
    }

    def __init__(self, json_base_path: str, csv_output_path: str):

        # Đường dẫn thư mục chứa các folder JSON theo từng quận
        self.json_base_path = json_base_path
        # Đường dẫn thư mục xuất các file CSV theo quận + file gộp
        self.csv_output_path = csv_output_path

        self.fieldnames = list(self.DATA_FORMAT.keys())


    # Chuyển từng quận từ JSON → CSV tương ứng
    def convert_json_to_csv(self):
        for dist in self.DISTRICT_NAMES:

            folder_path = os.path.join(self.json_base_path, f"bds_{dist}_data")
            file_csv_path = os.path.join(self.csv_output_path, f"bds_{dist}_data.csv")

            # Kiểm tra folder JSON
            if not os.path.exists(folder_path):
                print(f"[WARNING] Folder không tồn tại: {folder_path}")
                continue

            # Nếu CSV chưa tồn tại, ghi header
            write_header = not os.path.exists(file_csv_path)

            with open(file_csv_path, 'a', encoding='utf-8-sig', newline='') as file_csv:
                writer = csv.DictWriter(
                    file_csv,
                    fieldnames=self.fieldnames,
                    extrasaction='ignore'
                )

                if write_header:
                    writer.writeheader()

                for file_name in sorted(os.listdir(folder_path)):
                    file_path = os.path.join(folder_path, file_name)

                    with open(file_path, 'r', encoding='utf-8-sig') as f:
                        data = json.load(f)

                    # Khởi tạo row
                    row = {k: "" for k in self.fieldnames}

                    for k, v in data.items():
                        if k in row:
                            if isinstance(v, (list, dict)):
                                row[k] = json.dumps(v, ensure_ascii=False)
                            elif v is None:
                                row[k] = ""
                            else:
                                row[k] = v

                    writer.writerow(row)

            print(f"✓ Đã xử lý JSON → CSV cho quận {dist}")

    # Gộp tất cả file CSV thành một file
    def merge_csv_files(self, output_filename: str = "bds_full_data.csv"):
        dfs = []

        for dist in self.DISTRICT_NAMES:
            file_path = os.path.join(self.csv_output_path, f"bds_{dist}_data.csv")

            if not os.path.exists(file_path):
                print(f"[WARNING] Không tìm thấy file CSV: {file_path}")
                continue

            df = pd.read_csv(file_path)
            dfs.append(df)

        if not dfs:
            raise SystemExit("Không có file CSV nào để gộp.")

        all_df = pd.concat(dfs, ignore_index=True)

        # Xáo trộn dữ liệu cho đều
        all_df = all_df.sample(frac=1, random_state=42).reset_index(drop=True)

        output_path = os.path.join(self.csv_output_path, output_filename)
        all_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        print(f"✓ Đã gộp xong. Lưu tại: {output_path}")
        print(f"Tổng số dòng: {len(all_df)}")

    # Hàm chạy toàn bộ pipeline
    def process_all(self):

        print("=== BẮT ĐẦU XỬ LÝ JSON → CSV ===")
        self.convert_json_to_csv()
        print("=== HOÀN TẤT CHUYỂN JSON → CSV ===\n")

        print("=== BẮT ĐẦU GỘP CSV ===")
        self.merge_csv_files()
        print("=== HOÀN TẤT GỘP CSV ===")
        
if __name__ == "__main__":
    processor = RealEstateDataProcessor(
        json_base_path=r'C:\Users\Dinh Binh An\OneDrive\Dai_hoc\nhap_mon_python\final_project\project_root\Data\crawled_json_info',
        csv_output_path=r"C:\Users\Dinh Binh An\OneDrive\Dai_hoc\nhap_mon_python\final_project\project_root\Data\district_csv_data"
    )

    processor.process_all()
