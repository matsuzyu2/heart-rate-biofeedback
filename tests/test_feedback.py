"""
フィードバックモジュールのテストコード
"""
import unittest
from unittest.mock import Mock, patch, call
import os
import tempfile
from typing import List

# テスト対象のインポート（まだ実装されていないため最初は失敗する）
# Red フェーズ: 失敗するテストから開始
try:
    from src.feedback.audio_feedback import AudioFeedback
    from src.feedback.feedback_modes import (
        FeedbackMode, 
        IncreaseRewardMode, 
        DecreaseRewardMode, 
        RandomMode
    )
except ImportError:
    # テスト駆動なので、まだ実装されていない場合は None で進める
    AudioFeedback = None
    FeedbackMode = None
    IncreaseRewardMode = None
    DecreaseRewardMode = None
    RandomMode = None


class TestAudioFeedback(unittest.TestCase):
    """
    音声フィードバック機能のテスト
    """
    
    def setUp(self):
        """テスト前のセットアップ"""
        # テスト用の音声ファイルパスを設定
        self.reward_sound = "/path/to/reward.wav"
        self.punishment_sound = "/path/to/punishment.wav"
        
        # ファイル検証をモックして、テストでは実際のファイルが不要に
        if AudioFeedback:
            with patch('src.feedback.audio_feedback.Path.exists', return_value=True):
                with patch('src.feedback.audio_feedback.pygame.mixer.init'):
                    self.audio_feedback = AudioFeedback(
                        reward_sound=self.reward_sound,
                        punishment_sound=self.punishment_sound
                    )
    
    @unittest.skipIf(AudioFeedback is None, "AudioFeedback not implemented yet")
    @patch('src.feedback.audio_feedback.Path.exists', return_value=True)
    @patch('src.feedback.audio_feedback.pygame.mixer.init')
    def test_initialization(self, mock_mixer_init, mock_exists):
        """音声フィードバックの初期化テスト"""
        # Given: 音声ファイルパスが指定される
        reward_path = "/test/reward.wav"
        punishment_path = "/test/punishment.wav"
        
        # When: AudioFeedbackが初期化される
        feedback = AudioFeedback(reward_path, punishment_path)
        
        # Then: パスが正しく設定される
        self.assertEqual(feedback.reward_sound_path, reward_path)
        self.assertEqual(feedback.punishment_sound_path, punishment_path)
        
        # Then: ファイル存在チェックが実行される
        mock_exists.assert_called()
    
    @unittest.skipIf(AudioFeedback is None, "AudioFeedback not implemented yet")
    def test_initialization_with_missing_files(self):
        """存在しないファイルでの初期化エラーテスト"""
        # Given: 存在しないファイルパス
        reward_path = "/nonexistent/reward.wav"
        punishment_path = "/nonexistent/punishment.wav"
        
        # When & Then: AudioFeedbackErrorが発生する
        with self.assertRaises(Exception) as context:  # AudioFeedbackErrorがまだインポートされていない場合
            AudioFeedback(reward_path, punishment_path)
    
    @unittest.skipIf(AudioFeedback is None, "AudioFeedback not implemented yet")
    @patch('src.feedback.audio_feedback.pygame.mixer.Sound')
    def test_play_reward_sound(self, mock_sound_class):
        """報酬音再生のテスト"""
        # Given: AudioFeedbackが初期化されている
        mock_sound_instance = Mock()
        mock_sound_class.return_value = mock_sound_instance
        
        # When: 報酬音が再生される
        self.audio_feedback.play_reward()
        
        # Then: 正しい音声ファイルが再生される
        mock_sound_class.assert_called_with(self.reward_sound)
        mock_sound_instance.play.assert_called_once()
    
    @unittest.skipIf(AudioFeedback is None, "AudioFeedback not implemented yet")
    @patch('src.feedback.audio_feedback.pygame.mixer.Sound')
    def test_play_punishment_sound(self, mock_sound_class):
        """罰音再生のテスト"""
        # Given: AudioFeedbackが初期化されている
        mock_sound_instance = Mock()
        mock_sound_class.return_value = mock_sound_instance
        
        # When: 罰音が再生される
        self.audio_feedback.play_punishment()
        
        # Then: 正しい音声ファイルが再生される
        mock_sound_class.assert_called_with(self.punishment_sound)
        mock_sound_instance.play.assert_called_once()


class TestFeedbackModes(unittest.TestCase):
    """
    フィードバックモードのテスト
    """
    
    def setUp(self):
        """テスト前のセットアップ"""
        self.mock_audio = Mock()
        if IncreaseRewardMode:
            self.increase_mode = IncreaseRewardMode(self.mock_audio)
        if DecreaseRewardMode:
            self.decrease_mode = DecreaseRewardMode(self.mock_audio)
        if RandomMode:
            self.random_mode = RandomMode(self.mock_audio)
    
    @unittest.skipIf(IncreaseRewardMode is None, "IncreaseRewardMode not implemented yet")
    def test_increase_reward_mode_increasing_trend(self):
        """増加報酬モード: 上昇トレンドで報酬"""
        # Given: 心拍数が上昇傾向
        trend = "increasing"
        
        # When: フィードバックが処理される
        self.increase_mode.process_feedback(trend)
        
        # Then: 報酬音が再生される
        self.mock_audio.play_reward.assert_called_once()
        self.mock_audio.play_punishment.assert_not_called()
    
    @unittest.skipIf(IncreaseRewardMode is None, "IncreaseRewardMode not implemented yet")
    def test_increase_reward_mode_decreasing_trend(self):
        """増加報酬モード: 下降トレンドで罰"""
        # Given: 心拍数が下降傾向
        trend = "decreasing"
        
        # When: フィードバックが処理される
        self.increase_mode.process_feedback(trend)
        
        # Then: 罰音が再生される
        self.mock_audio.play_punishment.assert_called_once()
        self.mock_audio.play_reward.assert_not_called()
    
    @unittest.skipIf(DecreaseRewardMode is None, "DecreaseRewardMode not implemented yet")
    def test_decrease_reward_mode_decreasing_trend(self):
        """減少報酬モード: 下降トレンドで報酬"""
        # Given: 心拍数が下降傾向
        trend = "decreasing"
        
        # When: フィードバックが処理される
        self.decrease_mode.process_feedback(trend)
        
        # Then: 報酬音が再生される
        self.mock_audio.play_reward.assert_called_once()
        self.mock_audio.play_punishment.assert_not_called()
    
    @unittest.skipIf(RandomMode is None, "RandomMode not implemented yet")
    @patch('random.choice')
    def test_random_mode_random_feedback(self, mock_choice):
        """ランダムモード: ランダムフィードバック"""
        # Given: ランダムで報酬が選択される
        mock_choice.return_value = 'reward'
        trend = "stable"  # トレンドは無関係
        
        # When: フィードバックが処理される
        self.random_mode.process_feedback(trend)
        
        # Then: 報酬音が再生される
        self.mock_audio.play_reward.assert_called_once()


if __name__ == '__main__':
    unittest.main()