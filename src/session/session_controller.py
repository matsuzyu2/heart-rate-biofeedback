"""
セッション制御モジュール
実験セッションの基本的な開始・停止とコンポーネント統合を担当

設計原則:
- 単一責任原則（SRP）: セッション制御のみを責務とする
- YAGNI原則: 現在必要な機能のみを実装（最小限）
"""
import logging
from typing import Optional

from ..sensor.polar_interface import PolarInterface
from ..processing.heart_rate_processor import HeartRateProcessor
from ..feedback.feedback_modes import FeedbackMode

# ログ設定
logger = logging.getLogger(__name__)


class SessionController:
    """
    実験セッションの制御クラス（簡素版）
    
    責任:
    - セッションの開始・停止
    - コンポーネント間の基本的な統合
    - 心拍データからフィードバックへのデータフロー
    """
    
    def __init__(self, feedback_mode: FeedbackMode, device_id: Optional[str] = None):
        """
        SessionControllerの初期化
        
        Args:
            feedback_mode: フィードバックモードインスタンス
            device_id: Polarデバイス ID、Noneの場合は自動検出
        """
        self.feedback_mode = feedback_mode
        self.device_id = device_id
        
        # セッション状態（単純なフラグ）
        self.is_running = False
        
        # コンポーネント
        self.polar_interface: Optional[PolarInterface] = None
        self.heart_rate_processor: Optional[HeartRateProcessor] = None
        
        logger.info(f"SessionController initialized with mode: {type(feedback_mode).__name__}")
    
    async def start_session(self) -> bool:
        """
        セッションを開始
        
        Returns:
            bool: 開始成功時True、失敗時False
        """
        if self.is_running:
            logger.warning("Session is already running")
            return False
        
        logger.info("Starting session...")
        
        # コンポーネントの初期化
        if not await self._initialize_components():
            return False
        
        self.is_running = True
        logger.info("Session started successfully")
        return True
    
    async def stop_session(self) -> None:
        """
        セッションを停止
        """
        if not self.is_running:
            logger.warning("Session is not running")
            return
        
        logger.info("Stopping session...")
        
        # コンポーネントのクリーンアップ
        await self._cleanup_components()
        
        self.is_running = False
        logger.info("Session stopped successfully")
    
    async def _initialize_components(self) -> bool:
        """
        各コンポーネントの初期化
        
        Returns:
            bool: 初期化成功時True
        """
        try:
            # PolarInterfaceの初期化
            self.polar_interface = PolarInterface(device_id=self.device_id)
            
            # 接続試行
            if not await self.polar_interface.connect():
                logger.error("Failed to connect to Polar device")
                return False
            
            # HeartRateProcessorの初期化
            self.heart_rate_processor = HeartRateProcessor()
            
            # 心拍データのコールバック設定
            self.polar_interface.set_heart_rate_callback(self._on_heart_rate_data)
            
            # 心拍モニタリング開始
            if not await self.polar_interface.start_heart_rate_monitoring():
                logger.error("Failed to start heart rate monitoring")
                return False
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            await self._cleanup_components()
            return False
    
    async def _cleanup_components(self) -> None:
        """
        コンポーネントのクリーンアップ
        """
        if self.polar_interface:
            try:
                await self.polar_interface.stop_heart_rate_monitoring()
                await self.polar_interface.disconnect()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
            finally:
                self.polar_interface = None
        
        self.heart_rate_processor = None
        logger.info("Components cleaned up")
    
    def _on_heart_rate_data(self, heart_rate_data: dict) -> None:
        """
        心拍データ受信時のコールバック
        
        Args:
            heart_rate_data: 心拍データ（{"heart_rate": int, "timestamp": str}）
        """
        try:
            heart_rate = heart_rate_data.get("heart_rate")
            if heart_rate is None:
                logger.warning("Invalid heart rate data received")
                return
            
            # データ処理
            if self.heart_rate_processor:
                self.heart_rate_processor.add_heart_rate(heart_rate)
                
                # トレンド分析（最新3つのデータポイントでトレンドを判定）
                if len(self.heart_rate_processor.get_heart_rates()) >= 3:
                    trend = self.heart_rate_processor.get_current_trend()
                    
                    # フィードバック処理
                    self.feedback_mode.process_feedback(trend)
                    logger.debug(f"Feedback processed for trend: {trend}")
            
        except Exception as e:
            logger.error(f"Error processing heart rate data: {e}")