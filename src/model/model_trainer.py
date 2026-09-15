import argparse
import configparser
import logging
import json
import joblib
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor


# CLASS MODEL (BASE + LINEAR + R.FOREST + GRADIENT BOOSTING)
class BaseModel(ABC):
    """Lớp trừu tượng cho các model linear, random forest, gradient boosting,..."""

    @property
    @abstractmethod
    def name(self):
        '''Trả về tên model'''
        pass

    @abstractmethod
    def get_model(self):
        '''Trả về model'''
        pass

    @abstractmethod
    def get_param_grid(self):
        '''Trả về dictionary hyper-parameter của model'''
        pass

# MODEL 1: Linear Regression
class LinearRegressionModel(BaseModel):
    def __init__(self, param_grid=None):
        # param_grid: các hyperparameter để GridSearch
        self._param_grid = param_grid if param_grid is not None else {}

    @property
    def name(self):
        return "linear_regression"

    def get_model(self):
        return LinearRegression()

    def get_param_grid(self):
        return self._param_grid

# MODEL 2: Random Forest
class RandomForestModel(BaseModel):
    def __init__(self, random_state=42, param_grid=None):
        self.random_state = random_state
        self._param_grid = param_grid if param_grid is not None else {}

    @property
    def name(self):
        return "random_forest"

    def get_model(self):
        return RandomForestRegressor(random_state=self.random_state)

    def get_param_grid(self):
        return self._param_grid

# MODEL 3: Gradient Boosting
class GradientBoostingModel(BaseModel):
    def __init__(self, random_state=42, param_grid=None):
        self.random_state = random_state
        self._param_grid = param_grid if param_grid is not None else {}

    @property
    def name(self):
        return "gradient_boosting"

    def get_model(self):
        return GradientBoostingRegressor(random_state=self.random_state)

    def get_param_grid(self):
        return self._param_grid


# CLASS MODEL_TRAINER để tạo trainer thực thi việc training các model
class ModelTrainer:
    """
    Class ModelTrainer thực hiện các chức năng sau:
    - Load data
    - Split train/test
    - Train model
    - Optimize bằng GridSearchCV
    - Evaluate các metric RMSE, R2 và MAE
    - Save/load model
    - Ghi log + ghi kết quả CSV
    - Chạy nhiều mô hình và chọn ra mô hình tốt nhất

    Lưu ý: tất cả file kết quả (log, csv, hình, model) sẽ nằm trong `output_dir`.
    """

    def __init__(self, config_path: str, model_objects: list, output_dir: str = None):

        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        # Random state
        self.random_state = int(self.config["TRAINING"]["random_state"])
        np.random.seed(self.random_state)

        # Xác định output directory:
        if output_dir is not None:
            self.output_dir = Path(output_dir)
        else:
            out_from_config = self.config.get("OUTPUT", "output_dir", fallback=None)
            self.output_dir = Path(out_from_config) if out_from_config else Path("results")

        # Tạo output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # logging (Dùng file bên trong output_dir)
        log_file = self.output_dir / "training.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s",
            filemode="a"
        )
        logging.info(f"Output directory set to: {self.output_dir}")

        self.model_objects = model_objects
        self.best_model = None
        self.results = []
        self.X = None
        self.y = None
        self.data = None

    @staticmethod
    def rmse(y_true, y_pred):
        """ Tính RMSE """
        return np.sqrt(mean_squared_error(y_true, y_pred))

    
    def load_data(self, df: pd.DataFrame):
        """ Load dataset từ file CSV """
        target = self.config["DATA"]["target"]

        if target not in df.columns:
            raise ValueError(f"Target column '{target}' không tồn tại!")

        self.data = df.copy()
        self.X = df.drop(columns=[target])
        self.y = df[target]

        logging.info(f"Loaded data: {df.shape}")
        return self.X, self.y


    def split_data(self, X, y, test_size = 0.2):
        """ Chia tập train/test """
        test_size = float(self.config["TRAINING"]["test_size"])

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=self.random_state
        )
        logging.info("Split data thành công.")
        return self.X_train, self.X_test, self.y_train, self.y_test


    def optimize_params(self, model_obj, X_train, y_train):
        """Tối ưu tham số bằng GridSearchCV + ghi log chi tiết"""
        name = model_obj.name
        model = model_obj.get_model()
        param_grid = model_obj.get_param_grid()

        logging.info(f"--- GridSearchCV cho {name} ---")
        logging.info(f"param_grid = {param_grid}")

        cv = int(self.config["TRAINING"]["cv"])

        # Nếu param_grid rỗng => train thẳng
        if param_grid == {}:
            model.fit(X_train, y_train)
            return model

        search = GridSearchCV(
            model,
            param_grid=param_grid,
            cv=cv,
            scoring="neg_mean_squared_error",
            n_jobs=-1,
            verbose=1
        )
        search.fit(X_train, y_train)

        logging.info(f"[{name}] Best params: {search.best_params_}")
        return search.best_estimator_


    def train_model(self, model):
        """Huấn luyện mô hình"""

        model.fit(self.X_train, self.y_train)
        return model


    def evaluate(self, model):
        """
        Đánh giá mô hình bằng 3 metric chính:
            - RMSE
            - MAE
            - R2
        Trả về kết quả: self.metrics
        """
        y_pred = model.predict(self.X_test)

        return {
            "RMSE": np.sqrt(mean_squared_error(self.y_test, y_pred)),
            "MAE": mean_absolute_error(self.y_test, y_pred),
            "R2": r2_score(self.y_test, y_pred)
        }

    
    def save_model(self, path: str = None):
        """ Lưu model tốt nhất đã train """
        if path is None:
            path_obj = self.output_dir / "best_model.pkl"
        else:
            path_obj = Path(path)
            if not path_obj.is_absolute():
                path_obj = self.output_dir / path_obj

        joblib.dump(self.best_model, str(path_obj))
        logging.info(f"Model saved to {path_obj}")

    
    def load_model(self, path="best_model.pkl"):
        """ Load model """
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = self.output_dir / path_obj
        return joblib.load(str(path_obj))


    def experiment(self):
        """Chạy thử nghiệm với 3 mô hình và chọn mô hình tốt nhất"""

        if self.X_train is None:
            raise RuntimeError("Data chưa được split!")

        self.trained_models = {}

        for model_obj in self.model_objects:
            name = model_obj.name
            logging.info(f"===== Training model: {name} =====")

            best_m = self.optimize_params(model_obj, self.X_train, self.y_train)
            metrics = self.evaluate(best_m)

            self.trained_models[name] = best_m
            self.results.append({"model": name, **metrics})

        df_results = pd.DataFrame(self.results)
        results_csv_path = self.output_dir / "experiment_results.csv"
        df_results.to_csv(str(results_csv_path), index=False)
        logging.info(f"Experiment results saved to {results_csv_path}")

        # chọn model tốt nhất theo RMSE
        best_row = df_results.sort_values("RMSE").iloc[0]
        self.best_model_name = best_row["model"]
        self.best_model = self.trained_models[self.best_model_name]

        logging.info(f"BEST MODEL = {self.best_model_name}")

        # Trực quan kết quả so sánh 
        self.plot_results(df_results)


    def plot_results(self, df):
        """Trực quan kết quả"""
        plt.figure(figsize=(6, 4))
        plt.bar(df["model"], df["RMSE"])
        plt.ylabel("RMSE")
        plt.title("So sánh RMSE giữa các mô hình")
        plot_path = self.output_dir / "rmse_compare.png"
        plt.savefig(str(plot_path))
        logging.info(f"Plot saved to {plot_path}")
        plt.show()
        plt.close()

    def apply_model(self, feature_dict: dict):
        """
        Dự đoán giá trị đầu ra dựa trên mô hình tốt nhất.
        feature_dict: dict chứa các feature và giá trị của nó theo dạng:
            {"feature_1": val_1, 
            
            "feature_2": val_2,...}
        """

        if self.best_model is None:
            raise RuntimeError("Chưa có best_model. Hãy chạy experiment().")

        expected_cols = self.X_train.columns

        for col in expected_cols:
            if col not in feature_dict:
                feature_dict[col] = 0

        new_data = pd.DataFrame([{c: feature_dict[c] for c in expected_cols}])

        return float(self.best_model.predict(new_data)[0])
