"""
SessionControllerとHeartRateSessionLoggerの統合テスト
TDD: 統合機能のテスト
"""
import unittest
import tempfile
import os
import csv
from unittest.mock import Mock, AsyncMock

# テスト対象のインポート
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.session.session_controller import SessionController
from src.feedback.feedback_modes import FeedbackMode


class MockAudioFeedback:
    """テスト用のモック音声フィードバック"""
    def play_reward(self):
        pass
    
    def play_punishment(self):
        pass


class MockFeedbackMode(FeedbackMode):
    """テスト用のモックフィードバックモード"""
    def __init__(self):
        super().__init__(MockAudioFeedback())
    
    def process_feedback(self, trend):
        pass


class TestSessionControllerLoggingIntegration(unittest.TestCase):
    """
    SessionControllerとロギング機能の統合テスト
    """
    
    def setUp(self):
        """各テストの前に実行される初期化"""
        self.temp_dir = tempfile.mkdtemp()
        self.feedback_mode = MockFeedbackMode()
        
        # セッション情報
        self.session_info = {
            "subject_id": "TEST001",
            "session_type": "integration_test"
        }
    
    def tearDown(self):
        """各テストの後に実行されるクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_ログ機能付きセッション初期化(self):
        """ログ機能を有効にしたSessionControllerの初期化をテスト"""
        controller = SessionController(
            feedback_mode=self.feedback_mode,
            enable_logging=True,
            log_output_dir=self.temp_dir,
            session_info=self.session_info
        )
        
        # ロガーのセットアップを実行
        controller._setup_logging()
        
        # ロガーが初期化されていることを確認
        self.assertIsNotNone(controller.heart_rate_logger)
    
    def test_心拍データ受信時のログ保存(self):
        """心拍データ受信時にCSVファイルに保存されることをテスト"""
        controller = SessionController(
            feedback_mode=self.feedback_mode,
            enable_logging=True,
            log_output_dir=self.temp_dir,
            session_info=self.session_info
        )
        
        # セッションを開始（ロガーのセットアップ）
        controller._setup_logging()
        
        # テスト用心拍データ
        test_data = {
            "heart_rate": 75,
            "timestamp": "2024-01-01T12:00:00"
        }
        
        # 心拍データコールバックを直接呼び出し
        controller._on_heart_rate_data(test_data)
        
        # ファイルが作成されていることを確認
        files = os.listdir(self.temp_dir)
        csv_files = [f for f in files if f.endswith('.csv')]
        self.assertEqual(len(csv_files), 1)
        
        # ファイル内容を確認
        csv_file_path = os.path.join(self.temp_dir, csv_files[0])
        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['heart_rate'], '75')
        self.assertEqual(rows[0]['timestamp'], '2024-01-01T12:00:00')
    
    def test_ログ機能無効時_ログファイル未作成(self):
        """ログ機能を無効にした場合、ログファイルが作成されないことをテスト"""
        controller = SessionController(
            feedback_mode=self.feedback_mode,
            enable_logging=False
        )
        
        # テスト用心拍データ
        test_data = {
            "heart_rate": 75,
            "timestamp": "2024-01-01T12:00:00"
        }
        
        # 心拍データコールバックを直接呼び出し
        controller._on_heart_rate_data(test_data)
        
        # ロガーが存在しないことを確認
        self.assertIsNone(getattr(controller, 'heart_rate_logger', None))


if __name__ == '__main__':
    unittest.main()
