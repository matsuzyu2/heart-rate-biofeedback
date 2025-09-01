"""
HeartRateSessionLoggerクラスのテストコード
TDD: Red-Green-Refactorサイクルで実装
セッション管理機能のシンプルなテスト
"""
import unittest
import tempfile
import os
from datetime import datetime

# テスト対象のインポート
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.session.heart_rate_session_logger import HeartRateSessionLogger


class TestHeartRateSessionLogger(unittest.TestCase):
    """
    HeartRateSessionLoggerクラスのテスト
    責務: セッション管理とDataLoggerのラッパー機能
    """
    
    def setUp(self):
        """各テストの前に実行される初期化"""
        self.temp_dir = tempfile.mkdtemp()
        # セッション情報
        self.session_info = {
            "subject_id": "TEST001",
            "session_type": "baseline"
        }
        
    def tearDown(self):
        """各テストの後に実行されるクリーンアップ"""
        # 一時ディレクトリを削除
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_セッション開始_ファイル名生成(self):
        """セッション開始時に適切なファイル名が生成されることをテスト"""
        # Red: 最初は失敗する（HeartRateSessionLoggerクラス未実装のため）
        logger = HeartRateSessionLogger(
            output_dir=self.temp_dir,
            session_info=self.session_info
        )
        
        logger.start_session()
        
        # 新しいファイル名パターンをチェック（タイムスタンプ+連番）
        # 例: 20240901_143022_session_001.csv
        filename = logger.get_filename()
        parts = filename.split('_')
        
        self.assertEqual(len(parts), 4)  # date_time_session_number.csv
        self.assertEqual(parts[2], "session")
        self.assertTrue(parts[3].endswith(".csv"))
        self.assertTrue(parts[3].replace(".csv", "").isdigit())  # 連番部分が数字
    
    def test_心拍データ保存_ラッパー機能(self):
        """心拍データがDataLogger経由で保存されることをテスト"""
        logger = HeartRateSessionLogger(
            output_dir=self.temp_dir,
            session_info=self.session_info
        )
        logger.start_session()
        
        # テストデータ
        test_data = {
            "heart_rate": 75,
            "timestamp": "2024-01-01T12:00:00"
        }
        
        logger.log_heart_rate(test_data)
        
        # ファイルが作成されていることを確認
        file_path = os.path.join(self.temp_dir, logger.get_filename())
        self.assertTrue(os.path.exists(file_path))
    
    def test_セッション終了_ファイルクローズ(self):
        """セッション終了時に適切にファイルがクローズされることをテスト"""
        logger = HeartRateSessionLogger(
            output_dir=self.temp_dir,
            session_info=self.session_info
        )
        logger.start_session()
        
        # データを保存
        test_data = {"heart_rate": 75, "timestamp": "2024-01-01T12:00:00"}
        logger.log_heart_rate(test_data)
        
        # セッション終了
        logger.end_session()
        
        # ファイルが正常に作成されていることを確認
        file_path = os.path.join(self.temp_dir, logger.get_filename())
        self.assertTrue(os.path.exists(file_path))
    
    def test_複数セッション_異なるファイル名(self):
        """複数のセッションで異なるファイル名が生成されることをテスト"""
        # 1つ目のセッション
        logger1 = HeartRateSessionLogger(
            output_dir=self.temp_dir,
            session_info={"subject_id": "TEST001", "session_type": "baseline"}
        )
        logger1.start_session()
        filename1 = logger1.get_filename()
        
        # 2つ目のセッション（異なる設定）
        logger2 = HeartRateSessionLogger(
            output_dir=self.temp_dir,
            session_info={"subject_id": "TEST002", "session_type": "training"}
        )
        logger2.start_session()
        filename2 = logger2.get_filename()
        
        # ファイル名が異なることを確認
        self.assertNotEqual(filename1, filename2)


if __name__ == '__main__':
    unittest.main()
