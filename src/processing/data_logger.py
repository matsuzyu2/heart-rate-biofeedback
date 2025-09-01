"""
DataLoggerクラス - 心拍データのCSV保存機能
単一責任原則: CSVファイルへのデータ保存のみを責務とする
シンプルな実装でテストを通すことを優先
"""
import csv
import os
from typing import Dict, Any


class DataLogger:
    """
    心拍データをCSVファイルに保存するクラス
    
    責務:
    - CSVファイルの作成・管理
    - ヘッダーの自動追加
    - 心拍データの追記保存
    """
    
    def __init__(self, file_path: str):
        """
        DataLoggerを初期化
        
        Args:
            file_path (str): 保存先CSVファイルのパス
        """
        self.file_path = file_path
        self._initialize_csv_file()
    
    def _initialize_csv_file(self):
        """
        CSVファイルを初期化してヘッダーを書き込む
        ファイルが存在しない場合のみヘッダーを追加
        """
        # ディレクトリが存在しない場合は作成
        dir_path = os.path.dirname(self.file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # ファイルが存在しない場合のみヘッダーを追加
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'heart_rate'])
    
    def log_heart_rate(self, heart_rate_data: Dict[str, Any]):
        """
        心拍データをCSVファイルに追記保存
        
        Args:
            heart_rate_data (Dict[str, Any]): 心拍データ
                必須フィールド: 'timestamp', 'heart_rate'
                
        Raises:
            KeyError: 必須フィールドが欠落している場合
        """
        # 必須フィールドの存在確認
        if 'timestamp' not in heart_rate_data:
            raise KeyError("'timestamp' field is required")
        if 'heart_rate' not in heart_rate_data:
            raise KeyError("'heart_rate' field is required")
        
        # CSVファイルに追記
        with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                heart_rate_data['timestamp'],
                heart_rate_data['heart_rate']
            ])
