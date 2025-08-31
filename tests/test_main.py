"""
main.pyのテストコード
HeartRateBiofeedbackAppクラスの動作を検証

テスト方針:
- ユニットテスト: 各メソッドの単体テスト
- 統合テスト: アプリケーション全体の動作テスト
- モック使用: SessionControllerなどの外部依存をモック化
"""
import pytest
import asyncio
import argparse
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main import HeartRateBiofeedbackApp


class TestHeartRateBiofeedbackApp:
    """HeartRateBiofeedbackAppクラスのテストスイート"""
    
    @pytest.fixture
    def app(self):
        """テスト用のアプリケーションインスタンスを提供"""
        return HeartRateBiofeedbackApp()
    
    def test_initialization(self, app):
        """初期化のテスト"""
        assert app.session_controller is None
        assert app.shutdown_event is not None
    
    def test_create_feedback_mode_increase(self, app):
        """Increaseモードの作成テスト"""
        with patch('src.main.AudioFeedback') as mock_audio:
            with patch('src.main.IncreaseRewardMode') as mock_mode:
                mock_audio_instance = Mock()
                mock_audio.return_value = mock_audio_instance
                mock_mode_instance = Mock()
                mock_mode.return_value = mock_mode_instance
                
                result = app.create_feedback_mode("increase")
                
                # AudioFeedbackが適切な引数で呼ばれることを確認
                mock_audio.assert_called_once()
                args, kwargs = mock_audio.call_args
                assert len(args) == 2  # reward_sound, punishment_sound
                assert "high_sound.wav" in args[0]
                assert "low_sound.wav" in args[1]
                
                mock_mode.assert_called_once_with(mock_audio_instance)
                assert result == mock_mode_instance
    
    def test_create_feedback_mode_decrease(self, app):
        """Decreaseモードの作成テスト"""
        with patch('src.main.AudioFeedback') as mock_audio:
            with patch('src.main.DecreaseRewardMode') as mock_mode:
                mock_audio_instance = Mock()
                mock_audio.return_value = mock_audio_instance
                mock_mode_instance = Mock()
                mock_mode.return_value = mock_mode_instance
                
                result = app.create_feedback_mode("decrease")
                
                # AudioFeedbackが適切な引数で呼ばれることを確認
                mock_audio.assert_called_once()
                args, kwargs = mock_audio.call_args
                assert len(args) == 2  # reward_sound, punishment_sound
                assert "high_sound.wav" in args[0]
                assert "low_sound.wav" in args[1]
                
                mock_mode.assert_called_once_with(mock_audio_instance)
                assert result == mock_mode_instance
    
    def test_create_feedback_mode_random(self, app):
        """Randomモードの作成テスト"""
        with patch('src.main.AudioFeedback') as mock_audio:
            with patch('src.main.RandomMode') as mock_mode:
                mock_audio_instance = Mock()
                mock_audio.return_value = mock_audio_instance
                mock_mode_instance = Mock()
                mock_mode.return_value = mock_mode_instance
                
                result = app.create_feedback_mode("random")
                
                # AudioFeedbackが適切な引数で呼ばれることを確認
                mock_audio.assert_called_once()
                args, kwargs = mock_audio.call_args
                assert len(args) == 2  # reward_sound, punishment_sound
                assert "high_sound.wav" in args[0]
                assert "low_sound.wav" in args[1]
                
                mock_mode.assert_called_once_with(mock_audio_instance)
                assert result == mock_mode_instance
    
    def test_create_feedback_mode_invalid(self, app):
        """無効なモード名のテスト"""
        with pytest.raises(ValueError, match="Invalid feedback mode: invalid"):
            app.create_feedback_mode("invalid")
    
    def test_parse_arguments_increase_mode(self, app):
        """引数解析テスト - increaseモード"""
        test_args = ['--mode', 'increase']
        with patch('sys.argv', ['main.py'] + test_args):
            args = app.parse_arguments()
            assert args.mode == 'increase'
            assert args.device is None
            assert args.verbose is False
    
    def test_parse_arguments_with_device(self, app):
        """引数解析テスト - デバイス指定"""
        test_args = ['--mode', 'decrease', '--device', 'POLAR_H10_12345678']
        with patch('sys.argv', ['main.py'] + test_args):
            args = app.parse_arguments()
            assert args.mode == 'decrease'
            assert args.device == 'POLAR_H10_12345678'
            assert args.verbose is False
    
    def test_parse_arguments_with_verbose(self, app):
        """引数解析テスト - verboseオプション"""
        test_args = ['--mode', 'random', '--verbose']
        with patch('sys.argv', ['main.py'] + test_args):
            args = app.parse_arguments()
            assert args.mode == 'random'
            assert args.device is None
            assert args.verbose is True
    
    def test_setup_signal_handlers(self, app):
        """シグナルハンドラー設定のテスト"""
        with patch('signal.signal') as mock_signal:
            app.setup_signal_handlers()
            
            # SIGINT と SIGTERM のハンドラーが設定されることを確認
            assert mock_signal.call_count == 2
    
    @pytest.mark.asyncio
    async def test_shutdown_with_running_session(self, app):
        """実行中セッションありでのシャットダウンテスト"""
        mock_controller = AsyncMock()
        mock_controller.is_running = True
        app.session_controller = mock_controller
        
        await app.shutdown()
        
        mock_controller.stop_session.assert_called_once()
        assert app.shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_shutdown_without_session(self, app):
        """セッションなしでのシャットダウンテスト"""
        await app.shutdown()
        
        assert app.shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_shutdown_with_non_running_session(self, app):
        """停止中セッションでのシャットダウンテスト"""
        mock_controller = AsyncMock()
        mock_controller.is_running = False
        app.session_controller = mock_controller
        
        await app.shutdown()
        
        mock_controller.stop_session.assert_not_called()
        assert app.shutdown_event.is_set()


class TestArgumentParsing:
    """コマンドライン引数のテスト"""
    
    @pytest.fixture
    def app(self):
        return HeartRateBiofeedbackApp()
    
    def test_valid_modes(self, app):
        """有効なモードのテスト"""
        valid_modes = ['increase', 'decrease', 'random']
        
        for mode in valid_modes:
            test_args = ['--mode', mode]
            with patch('sys.argv', ['main.py'] + test_args):
                args = app.parse_arguments()
                assert args.mode == mode
    
    def test_missing_required_argument(self, app):
        """必須引数不足のテスト"""
        with patch('sys.argv', ['main.py']):
            with pytest.raises(SystemExit):
                app.parse_arguments()


@pytest.mark.integration
class TestMainIntegration:
    """main.pyの統合テスト"""
    
    @pytest.mark.asyncio
    async def test_app_run_with_mocked_components(self):
        """モック化されたコンポーネントでのアプリ実行テスト"""
        # テスト引数を設定
        test_args = ['main.py', '--mode', 'increase']
        
        with patch('sys.argv', test_args):
            with patch('src.main.AudioFeedback') as mock_audio:
                with patch('src.main.IncreaseRewardMode') as mock_mode:
                    with patch('src.main.SessionController') as mock_controller_class:
                        # モックの設定
                        mock_audio_instance = Mock()
                        mock_audio.return_value = mock_audio_instance
                        
                        mock_mode_instance = Mock()
                        mock_mode.return_value = mock_mode_instance
                        
                        mock_controller = AsyncMock()
                        mock_controller.start_session.return_value = True
                        mock_controller.is_running = True
                        mock_controller_class.return_value = mock_controller
                        
                        app = HeartRateBiofeedbackApp()
                        
                        # シャットダウンを即座に実行するタスクを作成
                        async def immediate_shutdown():
                            await asyncio.sleep(0.1)  # 少し待機
                            await app.shutdown()
                        
                        # 並行実行
                        shutdown_task = asyncio.create_task(immediate_shutdown())
                        
                        # アプリ実行
                        result = await app.run()
                        
                        # 結果確認
                        assert result == 0
                        mock_controller.start_session.assert_called_once()
                        mock_controller.stop_session.assert_called_once()
                        
                        # タスクの完了を待機
                        await shutdown_task
    
    @pytest.mark.asyncio
    async def test_app_run_session_start_failure(self):
        """セッション開始失敗時のテスト"""
        test_args = ['main.py', '--mode', 'increase']
        
        with patch('sys.argv', test_args):
            with patch('src.main.AudioFeedback'):
                with patch('src.main.IncreaseRewardMode'):
                    with patch('src.main.SessionController') as mock_controller_class:
                        mock_controller = AsyncMock()
                        mock_controller.start_session.return_value = False
                        mock_controller_class.return_value = mock_controller
                        
                        app = HeartRateBiofeedbackApp()
                        
                        result = await app.run()
                        
                        assert result == 1
                        mock_controller.start_session.assert_called_once()
