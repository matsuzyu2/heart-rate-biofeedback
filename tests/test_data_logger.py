"""
DataLoggerクラスのテストコード
TDD: Red-Green-Refactorサイクルで実装
シンプルな実装を目指す
"""
import unittest
import tempfile
import os
import csv
from datetime import datetime

# テスト対象のインポート
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.processing.data_logger import DataLogger


class TestDataLogger(unittest.TestCase):
    """
    DataLoggerクラスのテスト
    単一責任原則: CSVファイルへの心拍データ保存のみを責務とする
    """
    
    def setUp(self):
        """各テストの前に実行される初期化"""
        # 一時ファイルを作成（テスト後に自動削除）
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_session.csv")
        self.logger = DataLogger(self.test_file)
    
    def tearDown(self):
        """各テストの後に実行されるクリーンアップ"""
        # 一時ファイルを削除
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        os.rmdir(self.temp_dir)
    
    def test_初期化_ファイル作成(self):
        """初期化時にCSVファイルが作成されることをテスト"""
        # Red: 最初は失敗する（DataLoggerクラス未実装のため）
        self.assertTrue(os.path.exists(self.test_file))
    
    def test_ヘッダー_自動追加(self):
        """CSVヘッダーが自動追加されることをテスト"""
        with open(self.test_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertEqual(header, ['timestamp', 'heart_rate'])
    
    def test_心拍データ_単一保存(self):
        """単一の心拍データが正しく保存されることをテスト"""
        test_data = {
            "heart_rate": 75,
            "timestamp": "2024-01-01T12:00:00"
        }
        
        self.logger.log_heart_rate(test_data)
        
        # ファイル内容を確認
        with open(self.test_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['heart_rate'], '75')
        self.assertEqual(rows[0]['timestamp'], '2024-01-01T12:00:00')
    
    def test_心拍データ_複数保存(self):
        """複数の心拍データが順次追記されることをテスト"""
        test_data_list = [
            {"heart_rate": 70, "timestamp": "2024-01-01T12:00:00"},
            {"heart_rate": 75, "timestamp": "2024-01-01T12:00:01"},
            {"heart_rate": 80, "timestamp": "2024-01-01T12:00:02"}
        ]
        
        for data in test_data_list:
            self.logger.log_heart_rate(data)
        
        # ファイル内容を確認
        with open(self.test_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertEqual(len(rows), 3)
        for i, expected in enumerate(test_data_list):
            self.assertEqual(rows[i]['heart_rate'], str(expected['heart_rate']))
            self.assertEqual(rows[i]['timestamp'], expected['timestamp'])
    
    def test_無効なデータ_エラーハンドリング(self):
        """無効なデータに対するエラーハンドリングをテスト"""
        # 必須フィールドが欠落したデータ
        invalid_data = {"heart_rate": 75}  # timestampが欠落
        
        with self.assertRaises(KeyError):
            self.logger.log_heart_rate(invalid_data)


if __name__ == '__main__':
    unittest.main()
