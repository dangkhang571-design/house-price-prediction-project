> # **DỰ ÁN:** DỰ ĐOÁN GIÁ BẤT ĐỘNG SẢN TẠI THÀNH PHỐ HỒ CHÍ MINH

Tệp README này gồm hai phần chính: 
+ (A) pipeline crawl dữ liệu từ batdongsan.com
+ (B) pipeline tiền xử lý dữ liệu + huấn luyện mô hình cho bài toán regression. 


---

## MỤC LỤC

1. Tổng quan dự án
2. Yêu cầu & cài đặt
3. Cấu trúc thư mục mẫu
4. Phần A — Thu thập dữ liệu (crawl)

   * `crawl_url.py`
   * `crawl_bds_info.ipynb`
   * Kết quả đầu ra
5. Phần B — Tiền xử lý & Huấn luyện (Regression)

   * `PreprocessingData.py`
   * `model_trainer.py` / `main.py` (chạy mẫu)
6. Ví dụ chạy nhanh (Quickstarts)
7. Các lỗi thường gặp & cách khắc phục



---

# 1. Tổng quan dự án

Dự án gồm hai phần có thể chạy độc lập hoặc liên kết trong workflow:

* **Phần A — Crawl dữ liệu**: thu thập danh sách URL theo quận (listing pages), vào từng listing thu thập chi tiết (address, specs, giá,...) và lưu thành JSON, sau đó chuyển thành CSV per-quận và gộp toàn thành `bds_full_data.csv`.

* **Phần B — Pipeline tiền xử lý & huấn luyện (Regression)**: đọc dữ liệu đã xử lý, tiền xử lý (fill missing, scale, encode, xử lý outlier...), huấn luyện nhiều mô hình (Linear, RandomForest, GradientBoosting), so sánh kết quả, lưu model tốt nhất.

Bạn có thể dùng đầu ra của Phần A (`bds_full_data.csv`) làm dữ liệu đầu vào cho Phần B sau khi tiền xử lý.

---

# 2. Yêu cầu & cài đặt

* Python 3.8+ (khuyến nghị 3.9/3.10)
* Google Chrome (phiên bản tương thích với ChromeDriver)

**Tải package chính**:

```bash
pip install -r requirements.txt
```



# 3. Cấu trúc thư mục mẫu

```
project_root/
├── source_code/
    ├── crawl_data/
        ├── crawl_url_code/
            ├── crawl_url.py
        ├── crawl_info_code/
            ├── crawl_bds_info.ipynb
        ├── build_data/
            ├── build_full_data.py
    ├── model/           
        ├── model_trainer.py
        ├── config.ini
        ├── model_result/
            ├── best_model.pkl
            ├── experiment_results.csv
            ├── rmse_compare.png
            ├── training.log
    ├── preprocessing/
        ├── PreprocessingData.py
├── main/
    ├── main.py
├── requirements.txt
├── README.md
└── Data/
    ├── crawled_urls/
    │   ├── csv_urls/
    │   └── progress/
    ├── crawled_json_info/
        ├── bds_1_data
        ├── bds_2_data
        ................
        ├── bds_thu-duc_data
    ├── district_csv_data/      
```

---

# 4. PHẦN A — Thu thập dữ liệu (crawl)

Mục tiêu: thu thập dữ liệu listing bất động sản từ `batdongsan.com.vn` theo quận, lưu URL và chi tiết listing.

Lưu ý: Khi chạy code cần thay đổi địa chỉ cho phù hợp

## 4.1 `crawl_url.py` — thu thập danh sách URL

**Mục đích:** tạo `*_urls.csv` cho mỗi quận (các cột tối thiểu: `id`, `title`, `url`) và file progress để resume.

**Chạy:**

```bash
python crawl_url.py
```

**Cấu hình quan trọng (kiểm tra trong file):**

* `DEFAULT_BASE_PATH` — thư mục gốc lưu dữ liệu
* `DEFAULT_MAX_RETRY`, `DEFAULT_RETRY_DELAY` — retry khi lỗi
* `DEFAULT_HEADLESS` — chạy headless hay hiện trình duyệt
* `district_names` trong `__main__` — danh sách quận để crawl (giảm khi test)

**Kết quả:** CSV trong `Data/crawled_urls/csv_urls/` và file progress trong `Data/crawled_urls/progress/`.

## 4.2 `crawl_bds_info.ipynb` — thu thập chi tiết từng listing

**Mục đích:** đọc `*_urls.csv`, mở từng URL, trích xuất thông tin chi tiết như `address`, `specs`, `price`, `description`,... và lưu mỗi listing thành 1 file JSON trong folder `bds_{district}_data`.

**Chạy:**

1. Mở Jupyter Lab:

```bash
jupyter lab
```

2. Mở `crawl_bds_info.ipynb` và chạy các cell theo thứ tự.

*Hoặc* chuyển các cell chính ra script `.py` nếu muốn chạy không tương tác.

**Chú ý:**

* Trong notebook có tham số `file_name` (tên file CSV/quận) và `index_range` để giới hạn số listing test.
* Khi debug, set `headless=False` để quan sát trình duyệt.
* Notebook sử dụng `webdriver-manager` để tự động cài Chromedriver — nếu không, đảm bảo chromedriver phù hợp trên `PATH`.

**Kết quả:** Folder `bds_{district}_data/` chứa file JSON như `12345.json`.

## 4.3 `build_full_data.py` — chuyển JSON → CSV & gộp

**Mục đích:** chuyển tất cả JSON per-quận → CSV per-quận → gộp thành `bds_full_data.csv`.

**Chạy:**

```bash
python build_full_data.py
```

**Cấu hình trong `__main__` của file:**

* `json_base_path` — thư mục chứa các folder `bds_<district>_data`
* `csv_output_path` — nơi lưu CSV per-quận và file gộp

**Kết quả:** `bds_<district>_data.csv` cho từng quận và file `bds_full_data.csv`.


# 5. PHẦN B — Tiền xử lý & Huấn luyện mô hình (Regression)

Mục tiêu: dùng dữ liệu (ví dụ `bds_full_data.csv`) để tiền xử lý và huấn luyện mô hình hồi quy, so sánh kết quả và lưu model tốt nhất.

Lưu ý: Khi chạy code cần thay đổi địa chỉ cho phù hợp trong main code và config

## 5.1 `PreprocessingData.py` — lớp `DataPreprocessor`

**Chức năng chính:**

* Đọc file (CSV/JSON)
* Fill missing (median/mean/value/forward/backward)
* Chuyển text -> numeric (ví dụ: `"80 m²" -> 80`)
* Phát hiện & loại outlier (IQR, z-score)
* Scale numeric (StandardScaler/MinMax)
* Mã hóa biến phân loại (label encoding, one-hot)
* Trích features từ datetime
* Lưu DataFrame đã xử lý

**Ví dụ sử dụng:**

```python
from PreprocessingData import DataPreprocessor

prep = DataPreprocessor()
df = DataPreprocessor.read_file("Data/district_csv_data/bds_full_data.csv")
prep.df = df
prep.fill_missing(method="median", cols=['Price','Area'])
prep.clean_numeric_columns(['Area','Price'])
prep.encode_label('District','District_code')
num_cols, cat_cols = prep.classify_columns()
prep.scale(cols=num_cols, method='standard')
prep.save('Data/processed_real_estate.csv')
```

Lưu ý: `DataPreprocessor` nên giữ trạng thái các scaler/encoder (ví dụ `prep.scalers`, `prep.encoders`) để dùng lại cho dữ liệu mới khi deploy.

## 5.2 `model_trainer.py` — `ModelTrainer` và lớp model

`ModelTrainer` trong file này có signature `ModelTrainer(config_path: str, model_objects: list)`.

**Chức năng:**

* Đọc `config.ini` (ví dụ: `target`, `random_state`, `test_size`, `cv`)
* Nhận danh sách model objects (ví dụ `LinearRegressionModel`, `RandomForestModel`, `GradientBoostingModel`) kèm `param_grid`
* Thực hiện split dữ liệu, GridSearchCV (nếu param_grid không rỗng), huấn luyện, đánh giá theo RMSE/MAE/R2
* Lưu kết quả `experiment_results.csv`, biểu đồ so sánh (`rmse_compare.png`), `best_model.pkl`

**Ví dụ chạy:**

```python
from model_trainer import (
    ModelTrainer,
    LinearRegressionModel,
    RandomForestModel,
    GradientBoostingModel
)
import pandas as pd

# 1) chuẩn bị data (đã tiền xử lý)
df = pd.read_csv('Data/processed_real_estate.csv')

models = [
    LinearRegressionModel(param_grid={}),
    RandomForestModel(param_grid={
        'n_estimators': [100, 200],
        'max_depth': [None, 10]
    }),
    GradientBoostingModel(param_grid={
        'n_estimators': [100],
        'learning_rate': [0.1, 0.05]
    })
]

trainer = ModelTrainer(config_path='config.ini', model_objects=models)
trainer.load_data(df)
trainer.split_data(trainer.X, trainer.y)
trainer.experiment()
trainer.save_model('best_model.pkl')

print('Best model:', trainer.best_model_name)
```

**Outputs sinh ra:**

* `training.log` — log quá trình
* `experiment_results.csv` — kết quả cho mỗi model (RMSE, MAE, R2)
* `rmse_compare.png` — biểu đồ so sánh
* `best_model.pkl` — model tốt nhất (joblib dump)


---

# 6. Ví dụ chạy nhanh (Quickstarts)

## 6.1 Crawl một quận mẫu (test)

1. Mở `crawl_url.py`, chỉnh `district_names` chỉ 1 quận và `DEFAULT_HEADLESS=False` nếu muốn quan sát.
2. `python crawl_url.py` → kiểm tra file `Data/crawled_urls/csv_urls/<district>_urls.csv`.
3. Mở notebook `crawl_bds_info.ipynb`, set `file_name` tới file CSV trên và `index_range=range(10)` để run 10 listing đầu.
4. `python build_full_data.py` để gom JSON → CSV.

## 6.2 Tiền xử lý & train mẫu

1. `df = pd.read_csv('Data/district_csv_data/bds_full_data.csv')`
2. Dùng `PreprocessingData.DataPreprocessor` để tiền xử lý và lưu file processed.
3. Chạy script training mẫu (mã ví dụ ở §5.2).

# 7. Các lỗi thường gặp & cách khắc phục

* **Chromedriver mismatch**: lỗi tạo session → cài/chỉnh chromedriver cho đúng phiên bản Chrome hoặc dùng `webdriver-manager`.
* **Selectors thay đổi (CSS/XPath sai)**: Inspect trang, cập nhật selectors (ví dụ class tên `.js__card`, `.re__pagination-number`, ...).
* **Bị block / captcha**: giảm tốc, tăng delay, chạy ban đêm, sử dụng proxy/rotating IP (cân nhắc chính sách trang và pháp lý).
* **Lỗi ghi/đọc file**: kiểm tra permission thư mục, encoding (`utf-8-sig` khuyến nghị cho CSV với Excel). Có thể truyền địa chỉ thư mục hoặc là file sai.
* **Dữ liệu thiếu/format sai**: thêm validation trước khi convert; log các JSON lỗi để debug.



