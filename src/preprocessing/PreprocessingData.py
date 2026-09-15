import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder, OneHotEncoder, OrdinalEncoder
from sklearn.ensemble import IsolationForest
from pandas.api.types import is_numeric_dtype, is_string_dtype

class DataPreprocessor:
    def __init__(self, df=None):
        self.df = df
        self.scalers = {}
        self.encoders = {}
    
    def __repr__(self):
        return f"DataPreprocessor(data_shape={self.df.shape})"

    # Đọc dữ liệu
    @staticmethod
    def read_file(path, header='infer'):
        """
        Đọc dữ liệu theo định dạng file.
        Pandas sẽ tự xử lý header nếu header='infer'.
        """
        try:
            if path.endswith(".csv"):
                return pd.read_csv(path, header=header)
            elif path.endswith(".xlsx"):
                return pd.read_excel(path, header=header)
            elif path.endswith(".json"):
                return pd.read_json(path)
            else:
                raise ValueError("Unsupported file format.")
        except Exception as e:
            print("Error reading file:", e)
            return None
    
   
    # Xử lý missing values tùy theo kiểu dữ liệu
    def fill_missing(self, method, cols = None, value = None):
        """
        Điền giá trị còn thiếu theo phương pháp:
        - Categorical → mode() hoặc value
        - Numerical → mean/median/ffill/value      
        """
        try:
            target_cols = cols if cols is not None else self.df.columns

            for col in target_cols:

                # Cột dạng text/string
                if is_string_dtype(self.df[col]):
                    if method == "value" and value is not None:
                        # Điền bằng giá trị chỉ định
                        self.df[col] = self.df[col].fillna(value)
                    else:
                        # Mặc định → mode
                        mode_value = self.df[col].mode()
                        if len(mode_value) > 0:
                            self.df[col] = self.df[col].fillna(mode_value[0])

                 # Cột dạng số
                elif is_numeric_dtype(self.df[col]):
                    if method == "mean":
                        self.df[col] = self.df[col].fillna(self.df[col].mean())
                    elif method == "median":
                        self.df[col] = self.df[col].fillna(self.df[col].median())
                    elif method == "ffill":
                        self.df[col] = self.df[col].fillna(method="ffill")
                    elif method == "value":
                        if value is None:
                            raise ValueError(f"method='value' requires value parameter, missing for column {col}")
                        self.df[col] = self.df[col].fillna(value)
                    else:
                        raise ValueError(f"Invalid method '{method}' for numeric column '{col}'")
            
            return self.df
        
        except Exception as e:
            print(f"[ERROR] fill_missing failed: {e}")
            return self.df
    
    # Lọc các dòng phải có đủ các cột cần thiết
    def filter_by_required_features(self, required_features):
        """
        Giữ lại các dòng không thiếu dữ liệu ở danh sách cột yêu cầu.
        """
        try:
            df = self.df.dropna(subset=required_features)
            df = df[required_features]
            df = df.reset_index(drop=True)

            self.df = df
            return df
        except Exception as e:
            print(f"[ERROR] filter_by_required_features failed: {e}")
            return self.df

    # Phát hiện outliers (IQR, Z-score, IsolationForest)
    def find_outliers(self, col, method="iqr", z_thresh=3, contamination=0.03):
        """
        Trả về các dòng bị xem là outliers theo method.
        """
        try:
            series = self.df[col]

            if not is_numeric_dtype(series):
                print(f"Column {col} is not numeric. Skipping.")
                return pd.DataFrame()

            # IQR method
            if method == "iqr":
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                mask = (series < lower) | (series > upper)

            # Z-score
            elif method == "zscore":
                mean = series.mean()
                std = series.std()
                if std == 0:
                    print(f"Std = 0 → Cannot detect z-score outliers for {col}")
                    return pd.DataFrame()
                z = (series - mean) / std
                mask = z.abs() > z_thresh

            # Isolation Forest
            elif method == "isoforest":
                iso = IsolationForest(contamination=contamination, random_state=42)
                pred = iso.fit_predict(series.values.reshape(-1, 1))
                mask = pred == -1

            else:
                raise ValueError("Invalid method. Choose: iqr / zscore / isoforest")

            outliers = self.df[mask]

            print(f"\n=== OUTLIERS in '{col}' using {method} ===")
            print(f"Số lượng outliers: {outliers.shape[0]}")
            if outliers.shape[0] > 0:
                print("\nThống kê outliers:")
                print(outliers[[col]].describe())
            else:
                print("Không có outlier nào được phát hiện.")
            print("======================================\n")

            return outliers
        except Exception as e:
            print(f"[ERROR] find_outliers failed: {e}")
            return pd.DataFrame()
    
    # Xoá outliers khỏi df
    def clean_outliers(self, cols, method, z_thresh=3, contamination=0.03, show=False):
        """
        Xóa outliers theo từng cột trong danh sách.
        """
        try:
            df_clean = self.df.copy()

            for col in cols:
                if not is_numeric_dtype(df_clean[col]):
                    print(f"Column {col} is not numeric → skip")
                    continue  
                
                # Lấy outliers bằng chính hàm find_outliers()
                outliers = self.find_outliers(
                    col=col,
                    method=method,
                    z_thresh=z_thresh,
                    contamination=contamination
                )

                # Nếu không có outlier thì skip
                if outliers.empty:
                    print(f"No outliers to remove for column {col}")
                    continue

                # In mô tả nếu cần
                if show:
                    print(outliers[[col]].describe())

                # Xoá các dòng có index outlier
                df_clean = df_clean.drop(index=outliers.index)

                if df_clean.empty:
                    print(f"Warning: DataFrame became empty after removing outliers from {col}")
                    break

            return df_clean

        except Exception as e:
            print(f"[ERROR] clean_outliers failed: {e}")
            return self.df

    # Clean outliers dành riêng ngành bất động sản
    def clean_outliers_real_estate(
        self,
        col_area="Area",
        col_price="Price",
        col_bedroom="Bedroom_Number"
    ):
        """
        Loại các trường hợp bất hợp lý trong dữ liệu BĐS.
        """

        df = self.df.copy()

        # Kiểm tra cột tồn tại
        for c in [col_area, col_price, col_bedroom]:
            if c not in df.columns:
                raise ValueError(f"Column '{c}' not found in dataset")

        # Giới hạn percentile 
        for col in [col_area, col_price]:
            low = df[col].quantile(0.01)
            high = df[col].quantile(0.99)
            df = df[(df[col] >= low) & (df[col] <= high)]

        # Diện tích trung bình mỗi phòng
        df["room_size"] = df[col_area] / df[col_bedroom].replace(0, 1)

        # Loại trường hợp phi lý
        df = df[(df["room_size"] >= 8) & (df["room_size"] <= 80)]

        # Loại trường hợp phòng quá nhiều nhưng diện tích nhỏ
        df = df[~((df[col_bedroom] > 20) & (df[col_area] < 150))]

        # Bedroom hợp lý (dùng max 100 để tránh nhà trọ nhiều phòng)
        df = df[df[col_bedroom] <= 100]

        # Xóa cột phụ
        df = df.drop(columns=["room_size"], errors="ignore")
        df = df.reset_index(drop=True)

        return df

    
    # Chuẩn hóa dữ liệu
    def scale(self, cols, method):
        """
        Scale các cột số theo StandardScaler hoặc MinMaxScaler.
        """
        try:
            if method == "standard":
                scaler = StandardScaler()
            else:
                scaler = MinMaxScaler()

            self.df[cols] = scaler.fit_transform(self.df[cols])
            self.scalers[method] = scaler
            return self.df
        except Exception as e:
            print(f"[ERROR] scale failed: {e}")
            return self.df
    
    # Đổi tên cột
    def rename_columns(self, mapping: dict, errors="ignore"):
        """Đổi tên cột theo dict mapping."""
        try:
            self.df = self.df.rename(columns=mapping, errors=errors)
        except Exception as e:
            print("Error renaming columns:", e)
        return self.df
    

    # Mã hóa biến phân loại
    def encode_label(self, col, new_col):
        """Label Encoding cho 1 cột, lưu encoder để transform inverse khi cần."""
        try:
            le = LabelEncoder()
            self.df[new_col] = le.fit_transform(self.df[col].astype(str))
            self.encoders[new_col] = le
            return self.df
        except Exception as e:
            print(f"[ERROR] encode_label failed: {e}")
            return self.df
    
    def encode_onehot(self, cols):
        """One-Hot Encoding nhiều cột cùng lúc."""
        try:
            self.df = pd.get_dummies(self.df, columns=cols)
            return self.df
        except Exception as e:
            print(f"[ERROR] encode_onehot failed: {e}")
            return self.df
        
    def encode_ordinal(self, col, categories_order):
        """ Ordinal Encoding với thứ tự do người dùng quy định."""

        try:
            # Tạo encoder với danh sách categories theo chuẩn sklearn (list lồng list)
            encoder = OrdinalEncoder(categories=[categories_order])

            # reshape dữ liệu để sklearn xử lý
            values = self.df[[col]].astype(str)

            # fit + transform
            self.df[col] = encoder.fit_transform(values)

            # Lưu lại encoder
            self.encoders[col] = encoder

            return self.df

        except Exception as e:
            print(f"[ERROR] encode_ordinal failed for column '{col}': {e}")
            return self.df

    # Ánh xạ text theo keyword 
    def map_text_by_keywords(self, col, keyword_dict, default_value=None):
        """
        Gán giá trị mới dựa vào keyword xuất hiện trong text.
        """

        def map_one_value(text):
            if pd.isna(text):
                return default_value

            text_norm = str(text).lower()

            for val, keywords in keyword_dict.items():
                for kw in keywords:
                    if kw in text_norm:
                        return val
            
            return default_value

        self.df[col] = self.df[col].apply(map_one_value)
        return self.df
    

    # Chuẩn hóa text thành số (extract số trong chuỗi)
    @staticmethod
    def extract_number(text):
        """Lấy phần số trong chuỗi (80 m² → 80)."""

        if isinstance(text, (int, float)) and not pd.isna(text):
            return text

        if isinstance(text, str):
            text = text.replace(",", ".")
            nums = "".join([c if c.isdigit() or c == "." else " " for c in text]).strip()
            try:
                return float(nums.split()[0])
            except:
                return np.nan
        return np.nan

    def clean_numeric_columns(self, numeric_cols):
        """Chuyển các cột chứa text số → float."""
        try:
            for col in numeric_cols:
                self.df[col] = self.df[col].apply(self.extract_number)
            return self.df
        except Exception as e:
            print(f"[ERROR] clean_numeric_columns failed: {e}")
            return self.df

    # Phân loại cột số / cột phân loại
    def classify_columns(self):
        """Tách danh sách cột numerical và categorical."""
        df = self.df

        numerical_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()

        return numerical_cols, categorical_cols
    
    # Feature Engineering
    @staticmethod
    def add_price_per_area(df, price_col, area_col, new_col="Price_per_area", scale_price=1000):
        """
        Tạo feature mới: giá trên mỗi m2.

        df: DataFrame đầu vào (X_train, X_test hoặc full df)
        price_col: cột giá (y_train, Price,...)
        area_col: cột diện tích
        new_col: tên cột mới
        scale_price: hệ số nhân giá (vì y_train có thể đang chia 1000)

        Trả về dataframe có thêm cột mới.
        """
        try:
            df = df.copy()
            df[new_col] = df[price_col] * scale_price / df[area_col]
            return df
        except Exception as e:
            print(f"[ERROR] add_price_per_area failed: {e}")
            return df
        
    # Features thời gian
    def datetime_features(self, col):
        """
        Tạo các đặc trưng thời gian từ một cột datetime.
        """
        try:
            self.df[col] = pd.to_datetime(self.df[col], errors="coerce")
            self.df[f"{col}_year"] = self.df[col].dt.year
            self.df[f"{col}_month"] = self.df[col].dt.month
            self.df[f"{col}_day"] = self.df[col].dt.day
        except:
            print(f"Cannot parse datetime for column {col}")
        return self.df

    # Xóa dữ liệu trùng lặp
    def remove_duplicates(self, subset: list):
        """
        Loại bỏ các dòng trùng lặp trong list cột truyền vào
        """
        try:
            self.df = self.df.drop_duplicates(subset=subset)
            return self.df
        except Exception as e:
            print(f"[ERROR] remove_duplicates failed: {e}")
            return self.df

    # Xuất file
    def save(self, path):
        try:
            self.df.to_csv(path, index=False)
        except Exception as e:
            print(f"[ERROR] saving file failed: {e}")