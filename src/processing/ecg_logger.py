"""
ECGLoggerクラス - ECGデータのCSV保存機能
"""
import csv
import os
from typing import Dict, Any, List
from datetime import datetime

from ..config.ecg_config import ECG_LOG_DIRECTORY


class ECGLogger:
    """
    ECGデータをCSVファイルに保存するクラス
    """
    
    def __init__(self, file_path: str):
        """
        ECGLoggerを初期化
        
        Args:
            file_path (str): 保存先CSVファイルのパス
        """
        self.file_path = file_path
        self._initialize_csv_file()
    
    def _initialize_csv_file(self):
        """
        ECG用CSVファイルを初期化してヘッダーを書き込む
        """
        # ディレクトリが存在しない場合は作成
        dir_path = os.path.dirname(self.file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # ファイルが存在しない場合のみヘッダーを追加
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # ECGデータ用ヘッダー
                writer.writerow([
                    'timestamp_ns',
                    'ecg_value_μv'  # マイクロボルト単位のECGサンプル
                ])
    
    def log_ecg_data(self, ecg_data: Dict[str, Any]):
        """
        ECGデータをCSVファイルに追記保存
        
        Args:
            ecg_data (Dict[str, Any]): ECGデータ
                必須フィールド: 'ecg_samples', 'timestamps'
                
        Raises:
            KeyError: 必須フィールドが欠落している場合
            ValueError: データ長が一致しない場合
        """
        # 必須フィールドの存在確認
        required_fields = ['ecg_samples', 'timestamps']
        for field in required_fields:
            if field not in ecg_data:
                raise KeyError(f"'{field}' field is required")
        
        ecg_samples = ecg_data['ecg_samples']
        timestamps = ecg_data['timestamps']
        
        # データ長の整合性確認
        if len(ecg_samples) != len(timestamps):
            raise ValueError(f"Length mismatch: ecg_samples({len(ecg_samples)}) != timestamps({len(timestamps)})")
        
        # 各ECGサンプルを個別行として保存
        with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for ecg_value, timestamp_ns in zip(ecg_samples, timestamps):
                writer.writerow([
                    timestamp_ns,
                    ecg_value
                ])
    
    def log_multiple_ecg_data(self, ecg_data_list: List[Dict[str, Any]]):
        """
        複数のECGデータを一括でCSVファイルに追記保存
        
        Args:
            ecg_data_list (List[Dict[str, Any]]): ECGデータのリスト
        """
        for ecg_data in ecg_data_list:
            self.log_ecg_data(ecg_data)


def create_ecg_log_filename(base_name: str = "ecg_session") -> str:
    """
    ECGログファイル名を生成し、設定ファイルで指定されたディレクトリとの完全パスを返す
    
    Args:
        base_name (str): ベースファイル名
        
    Returns:
        str: 設定ディレクトリを含むタイムスタンプ付きファイルの完全パス
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{base_name}.csv"
    return os.path.join(ECG_LOG_DIRECTORY, filename)


def main():
    """ECGLoggerのテスト用メイン処理"""
    # テスト用ログファイル作成（設定ファイルのディレクトリを使用）
    test_log_path = create_ecg_log_filename("test")
    logger = ECGLogger(test_log_path)
    
    # テスト用ECGデータ
    test_ecg_data = {
        "ecg_samples": [0.1, 0.15, 0.2, 0.18, 0.12],
        "timestamps": [1694772000000000000, 1694772000007692307, 1694772000015384615, 1694772000023076923, 1694772000030769230]
    }
    
    # ECGデータをログ
    logger.log_ecg_data(test_ecg_data)
    print(f"ECG data logged to: {logger.file_path}")


if __name__ == "__main__":
    main()
