"""
sessionモジュールのテストコード
簡素化されたSessionControllerクラスの動作を検証

テスト方針:
- ユニットテスト: 各メソッドの単体テスト
- モック使用: 外部依存（Bluetoothデバイス）をモック化
- YAGNI原則: 現在実装されている機能のみをテスト
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.session.session_controller import SessionController
from src.feedback.feedback_modes import IncreaseRewardMode
from src.feedback.audio_feedback import AudioFeedback


class TestSessionController:
    """SessionControllerクラスのテストスイート"""
    
    @pytest.fixture
    def mock_audio_feedback(self):
        """モック化されたAudioFeedbackを提供"""
        mock = Mock(spec=AudioFeedback)
        mock.play_reward = Mock()
        mock.play_punishment = Mock()
        return mock
    
    @pytest.fixture
    def mock_feedback_mode(self, mock_audio_feedback):
        """モック化されたFeedbackModeを提供"""
        return IncreaseRewardMode(mock_audio_feedback)
    
    @pytest.fixture
    def session_controller(self, mock_feedback_mode):
        """テスト用のSessionControllerインスタンスを提供"""
        return SessionController(
            feedback_mode=mock_feedback_mode,
            device_id="test_device"
        )
    
    def test_initialization(self, session_controller, mock_feedback_mode):
        """初期化のテスト"""
        assert session_controller.feedback_mode == mock_feedback_mode
        assert session_controller.device_id == "test_device"
        assert session_controller.is_running is False
        assert session_controller.polar_interface is None
        assert session_controller.heart_rate_processor is None
    
    def test_is_running_when_idle(self, session_controller):
        """IDLE状態でのis_runningテスト"""
        assert session_controller.is_running is False
    
    def test_is_running_when_active(self, session_controller):
        """実行中状態でのis_runningテスト"""
        session_controller.is_running = True
        assert session_controller.is_running is True
    
    @pytest.mark.asyncio
    async def test_start_session_success(self, session_controller):
        """セッション開始成功のテスト"""
        with patch.object(session_controller, '_initialize_components', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True
            
            result = await session_controller.start_session()
            
            assert result is True
            assert session_controller.is_running is True
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_session_initialization_failure(self, session_controller):
        """セッション開始時の初期化失敗テスト"""
        with patch.object(session_controller, '_initialize_components', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = False
            
            result = await session_controller.start_session()
            
            assert result is False
            assert session_controller.is_running is False
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_session_already_running(self, session_controller):
        """既に実行中のセッション開始試行テスト"""
        session_controller.is_running = True
        
        result = await session_controller.start_session()
        
        assert result is False
        assert session_controller.is_running is True
    
    @pytest.mark.asyncio
    async def test_stop_session_success(self, session_controller):
        """セッション停止成功のテスト"""
        session_controller.is_running = True
        
        with patch.object(session_controller, '_cleanup_components', new_callable=AsyncMock) as mock_cleanup:
            await session_controller.stop_session()
            
            assert session_controller.is_running is False
            mock_cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_session_when_not_running(self, session_controller):
        """未実行時のセッション停止試行テスト"""
        initial_state = session_controller.is_running
        
        await session_controller.stop_session()
        
        # 状態が変更されないことを確認
        assert session_controller.is_running == initial_state
    
    @pytest.mark.asyncio
    async def test_initialize_components_success(self, session_controller):
        """コンポーネント初期化成功のテスト"""
        mock_polar = AsyncMock()
        mock_polar.connect.return_value = True
        mock_polar.start_heart_rate_monitoring.return_value = True
        mock_polar.set_heart_rate_callback = Mock()
        
        with patch('src.session.session_controller.PolarInterface', return_value=mock_polar):
            with patch('src.session.session_controller.HeartRateProcessor') as mock_processor:
                
                result = await session_controller._initialize_components()
                
                assert result is True
                assert session_controller.polar_interface == mock_polar
                assert session_controller.heart_rate_processor is not None
                mock_polar.connect.assert_called_once()
                mock_polar.start_heart_rate_monitoring.assert_called_once()
                mock_polar.set_heart_rate_callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_components_connection_failure(self, session_controller):
        """コンポーネント初期化時の接続失敗テスト"""
        mock_polar = AsyncMock()
        mock_polar.connect.return_value = False
        
        with patch('src.session.session_controller.PolarInterface', return_value=mock_polar):
            with patch.object(session_controller, '_cleanup_components', new_callable=AsyncMock):
                result = await session_controller._initialize_components()
                
                assert result is False
                mock_polar.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_components_monitoring_failure(self, session_controller):
        """心拍モニタリング開始失敗のテスト"""
        mock_polar = AsyncMock()
        mock_polar.connect.return_value = True
        mock_polar.start_heart_rate_monitoring.return_value = False
        mock_polar.set_heart_rate_callback = Mock()
        
        with patch('src.session.session_controller.PolarInterface', return_value=mock_polar):
            with patch('src.session.session_controller.HeartRateProcessor'):
                with patch.object(session_controller, '_cleanup_components', new_callable=AsyncMock):
                    result = await session_controller._initialize_components()
                    
                    assert result is False
                    mock_polar.start_heart_rate_monitoring.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_components(self, session_controller):
        """コンポーネントクリーンアップのテスト"""
        mock_polar = AsyncMock()
        session_controller.polar_interface = mock_polar
        session_controller.heart_rate_processor = Mock()
        
        await session_controller._cleanup_components()
        
        mock_polar.stop_heart_rate_monitoring.assert_called_once()
        mock_polar.disconnect.assert_called_once()
        assert session_controller.polar_interface is None
        assert session_controller.heart_rate_processor is None
    
    @pytest.mark.asyncio
    async def test_cleanup_components_with_error(self, session_controller):
        """クリーンアップ時のエラーテスト"""
        mock_polar = AsyncMock()
        mock_polar.stop_heart_rate_monitoring.side_effect = Exception("Test error")
        session_controller.polar_interface = mock_polar
        
        # エラーが発生してもクリーンアップが完了することを確認
        await session_controller._cleanup_components()
        
        assert session_controller.polar_interface is None
    
    def test_on_heart_rate_data_valid_data(self, session_controller):
        """有効な心拍データ処理のテスト"""
        mock_processor = Mock()
        mock_processor.get_heart_rates.return_value = [70, 72, 74, 76]  # 4つのデータポイント
        mock_processor.get_current_trend.return_value = "increasing"
        session_controller.heart_rate_processor = mock_processor
        
        mock_feedback_mode = Mock()
        session_controller.feedback_mode = mock_feedback_mode
        
        heart_rate_data = {"heart_rate": 75, "timestamp": "2024-01-01T12:00:00"}
        
        session_controller._on_heart_rate_data(heart_rate_data)
        
        mock_processor.add_heart_rate.assert_called_once_with(75)
        mock_processor.get_current_trend.assert_called_once()
        mock_feedback_mode.process_feedback.assert_called_once_with("increasing")
    
    def test_on_heart_rate_data_insufficient_data(self, session_controller):
        """データ不足時の心拍データ処理テスト"""
        mock_processor = Mock()
        mock_processor.get_heart_rates.return_value = [70, 72]  # 2つのデータポイント（不足）
        session_controller.heart_rate_processor = mock_processor
        
        mock_feedback_mode = Mock()
        session_controller.feedback_mode = mock_feedback_mode
        
        heart_rate_data = {"heart_rate": 75, "timestamp": "2024-01-01T12:00:00"}
        
        session_controller._on_heart_rate_data(heart_rate_data)
        
        mock_processor.add_heart_rate.assert_called_once_with(75)
        # フィードバック処理が呼ばれないことを確認
        mock_feedback_mode.process_feedback.assert_not_called()
    
    def test_on_heart_rate_data_invalid_data(self, session_controller):
        """無効な心拍データ処理のテスト"""
        mock_processor = Mock()
        session_controller.heart_rate_processor = mock_processor
        
        # 無効なデータ（heart_rateキーがない）
        heart_rate_data = {"timestamp": "2024-01-01T12:00:00"}
        
        session_controller._on_heart_rate_data(heart_rate_data)
        
        # プロセッサーが呼ばれないことを確認
        mock_processor.add_data.assert_not_called()
    
    def test_on_heart_rate_data_no_processor(self, session_controller):
        """プロセッサー未初期化時のテスト"""
        session_controller.heart_rate_processor = None
        
        heart_rate_data = {"heart_rate": 75, "timestamp": "2024-01-01T12:00:00"}
        
        # エラーが発生しないことを確認
        session_controller._on_heart_rate_data(heart_rate_data)


@pytest.mark.integration
class TestSessionControllerIntegration:
    """SessionControllerの統合テスト（簡素版）"""
    
    @pytest.mark.asyncio
    async def test_full_session_lifecycle_mock(self):
        """セッション全体のライフサイクルテスト（モック使用）"""
        # AudioFeedbackのモック
        mock_audio = Mock()
        mock_audio.play_reward = Mock()
        mock_audio.play_punishment = Mock()
        
        # FeedbackModeの作成
        feedback_mode = IncreaseRewardMode(mock_audio)
        
        # SessionControllerの作成
        controller = SessionController(feedback_mode=feedback_mode)
        
        # モックPolarInterfaceの設定
        mock_polar = AsyncMock()
        mock_polar.connect.return_value = True
        mock_polar.start_heart_rate_monitoring.return_value = True
        mock_polar.set_heart_rate_callback = Mock()
        
        with patch('src.session.session_controller.PolarInterface', return_value=mock_polar):
            with patch('src.session.session_controller.HeartRateProcessor'):
                # セッション開始
                start_result = await controller.start_session()
                assert start_result is True
                assert controller.is_running is True
                
                # セッション停止
                await controller.stop_session()
                assert controller.is_running is False