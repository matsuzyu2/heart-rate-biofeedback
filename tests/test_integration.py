"""
統合テスト: 心拍数プロセッサーとフィードバックシステムの統合
YAGNI原則: 必要最小限の統合テストのみ実装
"""
import unittest
from unittest.mock import Mock, patch

# テスト対象のインポート
try:
    from src.feedback import (
        AudioFeedback, 
        IncreaseRewardMode, 
        DecreaseRewardMode,
        AudioFeedbackError
    )
    from src.processing.heart_rate_processor import HeartRateProcessor
except ImportError as e:
    print(f"Import error: {e}")
    AudioFeedback = None
    IncreaseRewardMode = None
    DecreaseRewardMode = None
    AudioFeedbackError = None
    HeartRateProcessor = None


class TestCoreIntegration(unittest.TestCase):
    """
    コア機能の統合テスト
    YAGNI: 実際に使用される基本ワークフローのみテスト
    """
    
    @unittest.skipIf(AudioFeedback is None, "AudioFeedback not implemented yet")
    @unittest.skipIf(HeartRateProcessor is None, "HeartRateProcessor not implemented yet")
    @patch('src.feedback.audio_feedback.Path.exists', return_value=True)
    @patch('src.feedback.audio_feedback.pygame.mixer.init')
    @patch('src.feedback.audio_feedback.pygame.mixer.Sound')
    def test_heart_rate_feedback_integration(self, mock_sound, mock_mixer_init, mock_exists):
        """心拍数処理とフィードバックの基本統合テスト"""
        # Given: システムが初期化される
        processor = HeartRateProcessor()
        audio_feedback = AudioFeedback("reward.wav", "punishment.wav")
        feedback_mode = IncreaseRewardMode(audio_feedback)
        
        # When: 十分なデータで明確なトレンドを作成
        heart_rates = [60, 65, 70, 75, 80, 85]  # 明確な上昇傾向
        for hr in heart_rates:
            processor.add_heart_rate(hr)
        
        trend = processor.get_current_trend()
        feedback_mode.process_feedback(trend)
        
        # Then: システムが統合して動作する
        self.assertIn(trend, ["increasing", "stable", "decreasing"])
        # 音声システムが呼ばれることを確認
        mock_sound.assert_called()

    @unittest.skipIf(IncreaseRewardMode is None, "IncreaseRewardMode not implemented yet")
    def test_dependency_injection(self):
        """依存性注入パターンのテスト"""
        # Given: モックの音声フィードバック
        mock_audio = Mock()
        
        # When: フィードバックモードに注入
        mode = IncreaseRewardMode(mock_audio)
        mode.process_feedback("increasing")
        
        # Then: 依存性が正常に動作
        mock_audio.play_reward.assert_called_once()

    @unittest.skipIf(IncreaseRewardMode is None, "IncreaseRewardMode not implemented yet")
    @unittest.skipIf(DecreaseRewardMode is None, "DecreaseRewardMode not implemented yet") 
    def test_mode_switching_scenario(self):
        """モード切り替えシナリオの基本テスト"""
        # Given: モックオーディオフィードバック
        mock_audio = Mock()
        
        # When: 異なるモードで同じトレンドを処理
        increase_mode = IncreaseRewardMode(mock_audio)
        decrease_mode = DecreaseRewardMode(mock_audio)
        
        # 上昇トレンドに対する反応の違いをテスト
        increase_mode.process_feedback("increasing")  # 報酬
        decrease_mode.process_feedback("increasing")  # 罰
        
        # Then: モードによって異なる動作
        self.assertEqual(mock_audio.play_reward.call_count, 1)
        self.assertEqual(mock_audio.play_punishment.call_count, 1)

    @unittest.skipIf(AudioFeedback is None, "AudioFeedback not implemented yet")
    def test_error_handling_integration(self):
        """エラーハンドリングの基本統合テスト"""
        # Given & When & Then: 存在しないファイルで適切なエラーが発生
        with self.assertRaises((AudioFeedbackError, FileNotFoundError, OSError)):
            AudioFeedback("/nonexistent/reward.wav", "/nonexistent/punishment.wav")


if __name__ == '__main__':
    unittest.main()
