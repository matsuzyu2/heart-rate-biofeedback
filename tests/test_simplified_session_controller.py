"""
簡素化されたSessionControllerのテスト
デフォルトログ機能とシンプルなAPI
"""
import unittest
import tempfile
import os
import csv
from unittest.mock import Mock

# テスト対象のインポート
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.session.session_controller import SessionController


class MockAudioFeedback:
    """テスト用のモック音声フィードバック"""
    def play_reward(self):
        pass
    
    def play_punishment(self):
        pass


class MockFeedbackMode:
    """テスト用のモックフィードバックモード"""
    def __init__(self):
        self.audio_feedback = MockAudioFeedback()
    
    def process_feedback(self, trend):
        pass


class TestSimplifiedSessionController(unittest.TestCase):
    """
    簡素化されたSessionControllerのテスト
    """
    
    def setUp(self):
        """各テストの前に実行される初期化"""
        self.temp_dir = tempfile.mkdtemp()
        self.feedback_mode = MockFeedbackMode()
        
        # プロジェクトルートディレクトリをモック
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def tearDown(self):
        """各テストの後に実行されるクリーンアップ"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_デフォルト_ログ有効(self):
        """デフォルトでログ機能が有効になることをテスト"""
        controller = SessionController(feedback_mode=self.feedback_mode)
        
        # デフォルトでログが有効であることを確認
        self.assertTrue(controller.enable_logging)
        self.assertIsNotNone(controller.log_output_dir)
    
    def test_自動ディレクトリ作成(self):
        """logsディレクトリが自動作成されることをテスト"""
        controller = SessionController(feedback_mode=self.feedback_mode)
        controller._setup_logging()
        
        # logsディレクトリが作成されていることを確認
        logs_dir = os.path.join(self.temp_dir, "logs")
        self.assertTrue(os.path.exists(logs_dir))
    
    def test_タイムスタンプ連番ファイル名(self):
        """タイムスタンプ+連番のファイル名が生成されることをテスト"""
        controller = SessionController(feedback_mode=self.feedback_mode)
        controller._setup_logging()
        
        filename = controller.heart_rate_logger.get_filename()
        
        # ファイル名パターンをチェック
        # 例: 20240901_143022_session_001.csv
        parts = filename.split('_')
        self.assertEqual(len(parts), 4)  # date_time_session_number.csv
        self.assertEqual(parts[2], "session")
        self.assertTrue(parts[3].endswith(".csv"))
        self.assertTrue(parts[3].replace(".csv", "").isdigit())  # 連番部分が数字
    
    def test_複数セッション_連番増加(self):
        """複数のセッションで連番が増加することをテスト"""
        # 1つ目のセッション
        controller1 = SessionController(feedback_mode=self.feedback_mode)
        controller1._setup_logging()
        filename1 = controller1.heart_rate_logger.get_filename()
        
        # セッション終了をシミュレート
        controller1.heart_rate_logger.end_session()
        
        # 2つ目のセッション
        controller2 = SessionController(feedback_mode=self.feedback_mode)
        controller2._setup_logging()
        filename2 = controller2.heart_rate_logger.get_filename()
        
        # 連番が増加していることを確認
        num1 = int(filename1.split('_')[-1].replace('.csv', ''))
        num2 = int(filename2.split('_')[-1].replace('.csv', ''))
        self.assertGreater(num2, num1)
    
    def test_心拍データ自動保存(self):
        """心拍データが自動的に保存されることをテスト"""
        controller = SessionController(feedback_mode=self.feedback_mode)
        controller._setup_logging()
        
        # テスト用心拍データ
        test_data = {
            "heart_rate": 75,
            "timestamp": "2024-09-01T14:30:22"
        }
        
        controller._on_heart_rate_data(test_data)
        
        # ファイルが作成され、データが保存されていることを確認
        logs_dir = os.path.join(self.temp_dir, "logs")
        csv_files = [f for f in os.listdir(logs_dir) if f.endswith('.csv')]
        self.assertEqual(len(csv_files), 1)
        
        # ファイル内容を確認
        csv_file_path = os.path.join(logs_dir, csv_files[0])
        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['heart_rate'], '75')
    
    def test_ログ無効化オプション(self):
        """明示的にログを無効化できることをテスト"""
        controller = SessionController(
            feedback_mode=self.feedback_mode,
            enable_logging=False
        )
        
        # ログが無効であることを確認
        self.assertFalse(controller.enable_logging)
        self.assertIsNone(controller.heart_rate_logger)


if __name__ == '__main__':
    unittest.main()
