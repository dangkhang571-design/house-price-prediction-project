import os
import time
import random
import logging
import csv
import json
from datetime import datetime
from typing import Tuple, Set, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Các giá định mặc định
DEFAULT_BASE_PATH = r"C:\Users\Dinh Binh An\OneDrive\Dai_hoc\nhap_mon_python\final_project\project_root\Data\crawled_urls"
DEFAULT_PROGRESS_FILENAME = "progress.json"
DEFAULT_MAX_RETRY = 3       # số lần thử lại một trang khi lỗi
DEFAULT_RETRY_DELAY = 3     # thời gian nghỉ giữa mỗi lần thử
DEFAULT_HEADLESS = True     # chạy Chrome không giao diện


# cấu hình logging chung
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# Lớp phụ trách crawl link theo từng quận 
class DistrictCrawler:
    def __init__(
        self,
        base_path: str = DEFAULT_BASE_PATH,
        progress_filename: str = DEFAULT_PROGRESS_FILENAME,
        max_retry: int = DEFAULT_MAX_RETRY,
        retry_delay: int = DEFAULT_RETRY_DELAY,
        headless: bool = DEFAULT_HEADLESS,
    ):
        # Các thuộc tính cấu hình chính
        self.base_path = base_path
        self.progress_filename = progress_filename
        self.max_retry = max_retry
        self.retry_delay = retry_delay
        self.headless = headless

        # Logger riêng cho class
        self.logger = logging.getLogger(self.__class__.__name__)

        # Tạo các thư mục gốc
        os.makedirs(self.base_path, exist_ok=True)

        # Tạo thư mục lưu các url crawl được và folder lưu progress ở các quận
        self.csv_dir = os.path.join(self.base_path, "csv_urls")
        self.progress_dir = os.path.join(self.base_path, "progress")
        os.makedirs(self.csv_dir, exist_ok=True)
        os.makedirs(self.progress_dir, exist_ok=True)

    # Tạo Chrome driver 
    def make_driver(self) -> webdriver.Chrome:
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        # Một số flag giúp giảm lỗi và cải thiện tốc độ
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false") # tắt load ảnh để nhanh hơn
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Set user-agent để tránh bị website nghi ngờ bot
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(options=chrome_options)
        return driver

    # Trả về đường dẫn file CSV của một quận.
    def district_csv_path(self, district_name: str) -> str:
        return os.path.join(self.csv_dir, f"{district_name}_urls.csv")

    # Đọc CSV (nếu có) để load các URL đã lưu — tránh trùng lặp
    def load_existing_urls_from_csv(self, district_name: str) -> Set[str]:
        path = self.district_csv_path(district_name)
        urls = set()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        u = row.get("url")
                        if u:
                            urls.add(u)
            except Exception as e:
                self.logger.warning("Không đọc được file CSV %s: %s", path, e)
        return urls

    # Đọc CSV (nếu có) để load các URL đã lưu 
    def ensure_csv_header(self, path: str, fieldnames):
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

    # Ghi một link mới vào CSV,
    def append_link_to_csv(self, link: dict, district_name: str, existing_urls: Set[str]) -> bool:
        path = self.district_csv_path(district_name)
        fieldnames = ["id", "title", "url"]  
        self.ensure_csv_header(path, fieldnames)

        url = link.get("url")
        if not url:
            return False

        if url in existing_urls:
            return False

        row = {
            "id": link.get("id", ""),
            "title": link.get("title", ""),
            "url": url
        }
        try:
            with open(path, "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(row)
            existing_urls.add(url)
            self.logger.info("Ghi link mới vào %s: %s", path, url)
            return True
        except Exception as e:
            self.logger.error("Lỗi ghi CSV %s: %s", path, e)
            return False

    # Trả về đường dẫn file progress của một quận
    def progress_path(self, district_name: str) -> str:  
        return os.path.join(self.progress_dir, f"progress_{district_name}.json")

    # Đọc tiến độ (trang cuối đã crawl).
    def load_progress(self, district_name: str) -> Dict[str, int]:
        p = self.progress_path(district_name)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning("Không đọc được progress file %s: %s", p, e)
        return {}  # mặc định chưa có tiến độ

    # Ghi tiến độ crawl trang vào file JSON
    def save_progress(self, district_name: str, progress: Dict[str, int]):
        p = self.progress_path(district_name)
        try:
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            os.replace(tmp, p)
        except Exception as e:
            self.logger.error("Không lưu được progress vào %s: %s", p, e)

    # Cập nhật trang cuối đã crawl thành công.
    def update_progress(self, district_name: str, last_page: int):
        progress = {"last_page": last_page}
        self.save_progress(district_name, progress)
        self.logger.info("Cập nhật progress %s: trang %d", district_name, last_page)

    # Lấy số trang tối đa của một quận 
    def get_max_page(self, district_url: str) -> int:
        max_page = 1
        driver = None
        try:
            driver = self.make_driver()
            driver.get(district_url)
            time.sleep(random.uniform(1.0, 2.0))

            # cuộn xuống để trang tải đầy đủ phân trang
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CLASS_NAME, "re__pagination-group"))
            )

            page_links = driver.find_elements(By.CSS_SELECTOR, "a.re__pagination-number")
            page_numbers = [int(a.text.strip()) for a in page_links if a.text.strip().isdigit()]
            
            if page_numbers:
                max_page = max(page_numbers)

        except Exception as e:
            self.logger.warning("Không lấy được max page cho %s: %s", district_url, e)

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        self.logger.info("Quận %s -> Số trang max: %d", district_url, max_page)
        return max_page

    # Crawl link trên một trang
    def collect_links_for_page(self, page_url: str, district_name: str, existing_urls: Set[str]) -> Tuple[int, bool]:
        new_saved = 0
        tries = 0
        processed = False

        while tries < self.max_retry:
            driver = None
            try:
                driver = self.make_driver()
                driver.get(page_url)
                time.sleep(random.uniform(1.0, 2.0))

                scroll_times = random.randint(2, 4)
                for _ in range(scroll_times):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(random.uniform(0.7, 1.2))

                cards = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "js__card"))
                )

                for card in cards:
                    try:
                        a_tag = card.find_element(By.CLASS_NAME, "js__product-link-for-product-id")
                        url = a_tag.get_attribute("href")
                        title = a_tag.get_attribute("title")
                        item_id = card.get_attribute("prid")  # lấy atribut 'prid' làm id
                        if url:
                            link = {
                                "id": item_id,
                                "title": title,
                                "url": url
                            }
                            saved = self.append_link_to_csv(link, district_name, existing_urls)
                            if saved:
                                new_saved += 1
                     
                            print(url)
                    except Exception:
                        continue

                processed = True
                break  
            except (WebDriverException, TimeoutException) as e:
                tries += 1
                self.logger.warning("Lỗi load page %s (try %d/%d): %s", page_url, tries, self.max_retry, e)
                time.sleep(self.retry_delay)
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

        return new_saved, processed

    #  Crawl toàn bộ trang của một quận.
    def crawl_district(self, district_url: str, max_pages_limit: int = None) -> int:
        district_name = district_url.rstrip("/").split("-")[-1]
        existing_urls = self.load_existing_urls_from_csv(district_name)

        max_page = self.get_max_page(district_url)
        if max_pages_limit is not None:
            max_page = min(max_page, max_pages_limit)

        progress = self.load_progress(district_name)
        last_done = int(progress.get("last_page", 0))

        start_page = last_done + 1

        if start_page > max_page:
            self.logger.info("Quận %s: không có trang mới (start_page=%d, max_page=%d)", district_name, start_page, max_page)
            return 0

        total_new = 0
        for page_num in range(start_page, max_page + 1):
            page_url = district_url.rstrip("/") + f"/p{page_num}" if page_num > 1 else district_url
            self.logger.info("Crawl %s - Trang %d/%d", district_url, page_num, max_page)
            new_on_page, success = self.collect_links_for_page(page_url, district_name, existing_urls)
            if success:
                total_new += new_on_page
                self.update_progress(district_name, page_num)
            else:
                self.logger.error(
                    "Trang %s không xử lý được sau %d lần thử. Dừng crawl quận %s để resume sau.",
                    page_url,
                    self.max_retry,
                    district_name,
                )
                break

            time.sleep(random.uniform(1.0, 2.0))

        self.logger.info(
            "Quận %s: đã lưu %d link mới (tổng file hiện có: %d). Progress lưu ở %s",
            district_name,
            total_new,
            len(existing_urls),
            self.progress_path(district_name)
        )

        return total_new

    # Chạy crawl cho danh sách quận.
    def run(self, district_names: list, max_pages_limit: int = None) -> Dict[str, int]:
        results = {}
        for district_name in district_names:
            district_url = f'https://batdongsan.com.vn/nha-dat-ban-quan-{district_name}'
            try:
                count = self.crawl_district(district_url, max_pages_limit=max_pages_limit)
                
                self.logger.info("Quận %s: Thu được %d link mới trong lần chạy này", district_url, count)
                results[district_url] = count

            except Exception as e:
                self.logger.exception("Lỗi crawl quận %s: %s", district_url, e)

        return results



if __name__ == "__main__":
    
    # Danh sách tất cả quận TP.HCM trên batdongsan.com.vn
    district_names = [
        '1','2','3','4','5','6','7','8','9','10',
        '11','12','binh-thanh','phu-nhuan','binh-tan',
        'go-vap','tan-binh','tan-phu','binh-chanh',
        'can-gio','cu-chi','hoc-mon','nha-be','thu-duc'
    ]

    crawler = DistrictCrawler(
        base_path=DEFAULT_BASE_PATH,
        progress_filename=DEFAULT_PROGRESS_FILENAME,
        max_retry=DEFAULT_MAX_RETRY,
        retry_delay=DEFAULT_RETRY_DELAY,
        headless=DEFAULT_HEADLESS,
    )
    results = crawler.run(district_names, max_pages_limit=None)

    print("\nTổng hợp link mới thu được từng quận (lần chạy này):")
    for url, count in results.items():
        print(f"{url} -> {count} link mới")
