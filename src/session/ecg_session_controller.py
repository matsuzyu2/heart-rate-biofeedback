"""
ECGセッション制御モジュール
ECGベースの実験セッションの開始・停止とコンポーネント統合を担当
"""
import asyncio
import logging
from typing import Optional

from ..sensor.ecg_interface import ECGInterface
from ..processing.ecg_processor import ECGProcessor
from ..processing.simple_r_peak_detector import BeatEvent
from ..logger.ecg_logger import ECGLogger
from ..logger.beat_event_logger import BeatEventLogger
from ..logger.instantaneous_hr_logger import InstantaneousHRLogger
from ..feedback.feedback_modes import FeedbackMode

from ..config.ecg_config import (
    SESSION_DURATION_SECONDS
)

# ログ設定
logger = logging.getLogger(__name__)


class ECGSessionController:
    """
    ECGセッションの制御クラス
    
    役割:
    - ECGセッションの開始・停止
    - ECGInterface と ECGProcessor の統合
    - 5秒ごとのトレンド判定とフィードバック処理
    - ECGロギング機能の管理（BeatEvent, InstantaneousHR, ECG）
    """
    
    def __init__(
        self,
        feedback_mode: FeedbackMode,
        enable_logging: bool = True,
    ):
        """
        ECGSessionControllerの初期化
        
        Args:
            feedback_mode: フィードバックモードインスタンス
            enable_logging: ログ機能を有効にするかどうか（デフォルト: True）
        """
        self.feedback_mode = feedback_mode
        
        # ログ機能の設定（デフォルトで有効）
        self.enable_logging = enable_logging
        
        # ロガー
        self.beat_logger: Optional[BeatEventLogger] = None
        self.instantaneous_hr_logger: Optional[InstantaneousHRLogger] = None
        self.ecg_logger: Optional[ECGLogger] = None
        
        # セッション状態（単純なフラグ）
        self.is_running = False
        
        # コンポーネント
        self.ecg_interface: Optional[ECGInterface] = None
        self.ecg_processor: Optional[ECGProcessor] = None
        
        # フィードバックタイマー用のタスク
        self._feedback_task: Optional[asyncio.Task] = None
        
        # セッション自動終了タイマー用のタスク
        self._session_timer_task: Optional[asyncio.Task] = None
        
        logger.info(f"ECGSessionController initialized with mode: {type(feedback_mode).__name__}")
    
    async def start_session(self) -> bool:
        """
        ECGセッションを開始
        
        Returns:
            bool: 開始成功時True、失敗時False
        """
        if self.is_running:
            logger.warning("ECG session is already running")
            return False
        
        logger.info("Starting ECG session...")
        
        # ログ機能のセットアップ
        if self.enable_logging:
            self._setup_logging()
        
        # コンポーネントの初期化
        if not await self._initialize_components():
            return False
        
        # フィードバックタイマーの開始
        self._feedback_task = asyncio.create_task(self._feedback_timer_loop())
        
        # セッション自動終了タイマーの開始
        self._session_timer_task = asyncio.create_task(self._session_timer())
        
        self.is_running = True
        logger.info("ECG session started successfully")
        return True
    
    async def stop_session(self) -> None:
        """
        ECGセッションを停止
        """
        if not self.is_running:
            logger.warning("ECG session is not running")
            return
        
        logger.info("Stopping ECG session...")
        
        # セッション停止フラグを設定
        self.is_running = False
        
        # フィードバックタイマーの停止
        if self._feedback_task:
            self._feedback_task.cancel()
            try:
                await self._feedback_task
            except asyncio.CancelledError:
                pass
            self._feedback_task = None
        
        # セッション自動終了タイマーの停止
        if self._session_timer_task:
            self._session_timer_task.cancel()
            try:
                await self._session_timer_task
            except asyncio.CancelledError:
                pass
            self._session_timer_task = None
        
        # ログ機能の終了
        if self.beat_logger:
            self.beat_logger.end_session()
            self.beat_logger = None
        
        if self.instantaneous_hr_logger:
            self.instantaneous_hr_logger.end_session()
            self.instantaneous_hr_logger = None
        
        if self.ecg_logger:
            self.ecg_logger.end_session()
            self.ecg_logger = None
        
        # コンポーネントのクリーンアップ
        await self._cleanup_components()
        
        logger.info("ECG session stopped successfully")
    
    async def _initialize_components(self) -> bool:
        """
        各コンポーネントの初期化
        
        Returns:
            bool: 初期化成功時True
        """
        try:
            # ECGInterfaceの初期化
            self.ecg_interface = ECGInterface()
            
            # 接続試行
            if not await self.ecg_interface.connect():
                logger.error("Failed to connect to ECG device")
                return False
            
            # ECGProcessorの初期化
            self.ecg_processor = ECGProcessor()
            
            # ビート検出時のコールバック設定（ロギング用）
            self.ecg_processor.set_beat_callback(self._on_beat_detected)
            
            # ECGデータのコールバック設定
            self.ecg_interface.set_ecg_callback(self._on_ecg_data)
            
            # ECGモニタリング開始
            if not await self.ecg_interface.start_ecg_streaming():
                logger.error("Failed to start ECG monitoring")
                return False
            
            logger.info("All ECG components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"ECG component initialization failed: {e}")
            await self._cleanup_components()
            return False
    
    async def _cleanup_components(self) -> None:
        """
        コンポーネントのクリーンアップ
        """
        if self.ecg_interface:
            try:
                await self.ecg_interface.stop_ecg_streaming()
                await self.ecg_interface.disconnect()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
            finally:
                self.ecg_interface = None
        
        self.ecg_processor = None
        logger.info("ECG components cleaned up")
    
    async def _feedback_timer_loop(self) -> None:
        """
        5秒ごとのフィードバック処理ループ
        """
        while self.is_running:
            await asyncio.sleep(5.0)  # 5秒待機
            
            if self.is_running and self.ecg_processor:
                try:
                    # トレンド判定を取得
                    trend = self.ecg_processor.get_heart_rate_trend()
                    
                    # フィードバック処理
                    self.feedback_mode.process_feedback(trend)
                    
                    logger.debug(f"Feedback processed for trend: {trend}")
                    
                except Exception as e:
                    logger.error(f"Error in feedback timer: {e}")
    
    async def _session_timer(self) -> None:
        """
        セッション自動終了タイマー
        """

        duration = SESSION_DURATION_SECONDS
        
        try:
            # 設定時間のログ出力
            minutes = duration / 60.0
            logger.info(f"Session will automatically stop after {duration} seconds ({minutes:.1f} minutes)")
            
            # 設定時間待機
            await asyncio.sleep(duration)
            
            # 自動終了のログ出力
            if self.is_running:
                await self.stop_session()
                
        except asyncio.CancelledError:
            # 手動停止された場合
            logger.debug("Session timer cancelled (manual stop)")
            raise
        except Exception as e:
            logger.error(f"Error in session timer: {e}")
    
    def _on_ecg_data(self, ecg_data: dict) -> None:
        """
        ECGデータ受信時のコールバック
        
        Args:
            ecg_data: ECGデータ（{"ecg_samples": List[float], "timestamps": List[int]}）
        """
        try:
            # データ処理
            if self.ecg_processor:
                self.ecg_processor.add_ecg_data(ecg_data)
            
            # ECGログ機能: ECGデータをCSVファイルに保存
            if self.ecg_logger:
                self.ecg_logger.log_ecg(ecg_data)
            
            # Beat/InstantaneousHRのロギングは _on_beat_detected で実行
            # （ECGProcessorの内部コールバックから呼び出される想定）
            
        except Exception as e:
            logger.error(f"Error processing ECG data: {e}")
    
    def _on_beat_detected(self, beat_event: BeatEvent) -> None:
        """
        R波検出時のコールバック（ロギング用）
        
        Args:
            beat_event (BeatEvent): 検出されたR波イベント
        """
        try:
            # BeatEventLoggerでロギング
            if self.beat_logger:
                beat_data = {
                    "timestamp_ns": beat_event.timestamp_ns,
                    "sample_index": beat_event.sample_index,
                    "amplitude": beat_event.amplitude,
                    "rr_interval_ms": beat_event.rr_interval_ms
                }
                self.beat_logger.log_beat(beat_data)
            
            # InstantaneousHRLoggerでロギング
            # RR間隔が有効な場合のみ（最初のビートはスキップ）
            if self.instantaneous_hr_logger and beat_event.rr_interval_ms is not None:
                instantaneous_hr_bpm = 60000.0 / beat_event.rr_interval_ms
                instantaneous_hr_data = {
                    "timestamp_ns": beat_event.timestamp_ns,
                    "rr_interval_ms": beat_event.rr_interval_ms,
                    "instantaneous_hr_bpm": instantaneous_hr_bpm
                }
                self.instantaneous_hr_logger.log_instantaneous_hr(instantaneous_hr_data)
                
        except Exception as e:
            logger.error(f"Error in beat detected callback: {e}")
    
    def _setup_logging(self) -> None:
        """
        ログ機能のセットアップ
        """
        if not self.enable_logging:
            return
        
        try:
            # BeatEventLoggerの初期化（デフォルト: ecg_config.BEAT_LOG_DIRECTORY）
            self.beat_logger = BeatEventLogger()
            self.beat_logger.start_session()
            logger.info(f"Beat logging enabled: {self.beat_logger.get_filename()}")
            
            # InstantaneousHRLoggerの初期化（デフォルト: ecg_config.INSTANTANEOUS_HR_LOG_DIRECTORY）
            self.instantaneous_hr_logger = InstantaneousHRLogger()
            self.instantaneous_hr_logger.start_session()
            logger.info(f"Instantaneous HR logging enabled: {self.instantaneous_hr_logger.get_filename()}")
            
            # ECGLoggerの初期化（デフォルト: ecg_config.ECG_LOG_DIRECTORY）
            self.ecg_logger = ECGLogger()
            self.ecg_logger.start_session()
            logger.info(f"ECG logging enabled: {self.ecg_logger.get_filename()}")
            
        except Exception as e:
            logger.error(f"Failed to setup logging: {e}")
            # エラーが発生してもセッションは継続可能
            self.beat_logger = None
            self.instantaneous_hr_logger = None
            self.ecg_logger = None
