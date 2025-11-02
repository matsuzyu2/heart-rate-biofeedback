# ECG専用データ処理・解析
from typing import List, Dict, Any, Optional, Callable, Tuple
import logging

# R波検出器をインポート
from .simple_r_peak_detector import SimpleRPeakDetector, BeatEvent
# 瞬間心拍数算出クラスをインポート
from .instantaneous_heart_rate import InstantaneousHeartRate, TrendType
# ECG設定をインポート
from ..config.ecg_config import ECG_SAMPLING_RATE, HR_BLOCK_WINDOW_SECONDS

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ECGDataValidator:
    """
    ECGデータの妥当性検証クラス
    """
    
    def is_valid_ecg_data(self, ecg_data):
        """
        ECGデータの妥当性を検証
        
        Args:
            ecg_data: 検証するECGデータ
            
        Returns:
            bool: データが有効であればTrue
        """
        if not ecg_data:
            return False
            
        if 'ecg_samples' not in ecg_data or 'timestamps' not in ecg_data:
            return False
            
        if not isinstance(ecg_data['ecg_samples'], list):
            return False
            
        if not isinstance(ecg_data['timestamps'], list):
            return False
            
        return True


class ECGProcessor:
    """
    ECGデータプロセッサー（メインクラス）
    R波検出機能を統合
    """
    
    def __init__(self, sampling_rate: Optional[int] = None):
        """
        ECGプロセッサーの初期化
        
        Args:
            sampling_rate (Optional[int]): サンプリング周波数（Hz）。
                                         Noneの場合はecg_config.pyから取得
        """
        self.ecg_data_list: List[Dict[str, Any]] = []
        self.validator = ECGDataValidator()
        
        # R波検出器の初期化
        self.sampling_rate = sampling_rate or ECG_SAMPLING_RATE
        self.r_peak_detector = SimpleRPeakDetector(self.sampling_rate)
        
        # 瞬間心拍数算出器の初期化
        self.instantaneous_hr = InstantaneousHeartRate()
        
        # 外部コールバック（セッションコントローラー用）
        self.beat_callback: Optional[Callable[[BeatEvent], None]] = None
        
        # R波検出時の内部コールバックを設定
        self.r_peak_detector.set_beat_callback(self._on_beat_detected)
    
    def _on_beat_detected(self, beat_event: BeatEvent) -> None:
        """
        R波検出時の内部コールバック処理
        
        Args:
            beat_event (BeatEvent): 検出されたR波イベント
        """
        # InstantaneousHeartRateにビートイベントを送信
        self.instantaneous_hr.add_beat_event(beat_event)
        
        # 外部コールバックがあれば実行（セッションコントローラーへの通知）
        if self.beat_callback:
            self.beat_callback(beat_event)
    
    def set_beat_callback(self, callback: Callable[[BeatEvent], None]) -> None:
        """
        R波検出時の外部コールバック関数を設定
        
        Args:
            callback: R波検出時に呼び出される関数
        """
        self.beat_callback = callback
    
    def add_ecg_data(self, ecg_data):
        """
        ECGデータを追加し、R波検出を実行
        
        Args:
            ecg_data: 追加するECGデータ
            
        Returns:
            bool: 追加に成功した場合True
        """
        if not self.validator.is_valid_ecg_data(ecg_data):
            return False
            
        self.ecg_data_list.append(ecg_data)
        
        # R波検出を実行
        try:
            samples = ecg_data.get('ecg_samples', [])
            timestamps = ecg_data.get('timestamps', [])
            
            if samples and timestamps:
                detected_beats = self.r_peak_detector.add_samples(samples, timestamps)
                
                if detected_beats:
                    logger.info(f"Detected {len(detected_beats)} R-peaks in current data chunk")
                    
        except Exception as e:
            logger.error(f"Error in R-peak detection: {e}")
        
        return True
    
    def get_ecg_data_count(self) -> int:
        """
        保存されているECGデータの件数を取得
        
        Returns:
            int: ECGデータの件数
        """
        return len(self.ecg_data_list)
    
    def get_total_samples(self) -> int:
        """
        総サンプル数を取得
        
        Returns:
            int: 全ECGデータの総サンプル数
        """
        total = 0
        for ecg_data in self.ecg_data_list:
            ecg_samples = ecg_data.get("ecg_samples", [])
            total += len(ecg_samples)
        return total
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        セッション全体の要約情報を取得
        
        Returns:
            Dict: セッション要約情報
        """
        data_count = self.get_ecg_data_count()
        total_samples = self.get_total_samples()
        
        summary = {
            "data_count": data_count,
            "total_samples": total_samples,
            "duration_seconds": 0.0
        }
        
        if self.ecg_data_list:
            # セッション開始・終了時刻（ナノ秒形式）
            first_data = self.ecg_data_list[0]
            latest_data = self.ecg_data_list[-1]
            
            # 最初と最後のタイムスタンプを取得
            first_timestamps = first_data.get("timestamps", [])
            latest_timestamps = latest_data.get("timestamps", [])
            
            if first_timestamps and latest_timestamps:
                # ナノ秒単位のタイムスタンプから秒単位に変換
                start_timestamp_ns = first_timestamps[0]
                end_timestamp_ns = latest_timestamps[-1]
                
                # セッション時間を秒単位で計算
                duration_ns = end_timestamp_ns - start_timestamp_ns
                summary["duration_seconds"] = duration_ns / 1_000_000_000
        
        return summary
    
    def get_heart_rate_bpm(self, window_duration_ms: Optional[int] = None) -> Optional[float]:
        """
        現在の心拍数を取得（InstantaneousHeartRateベース）
        
        Args:
            window_duration_ms (Optional[int]): 計算窓の時間幅（ミリ秒）、Noneの場合は設定ファイルから取得
            
        Returns:
            Optional[float]: 心拍数（BPM）、計算できない場合はNone
        """
        # 時間窓を決定（設定ファイルからデフォルト値を取得）
        if window_duration_ms is None:
            window_duration_s = HR_BLOCK_WINDOW_SECONDS
        else:
            window_duration_s = window_duration_ms / 1000.0
        
        # ブロック平均を取得
        block_averages = self.instantaneous_hr.get_block_averages(window_seconds=window_duration_s)
        
        # 最新のブロック平均を返す
        latest_block = block_averages[-1]
        return latest_block["average_hr"]
    
    def get_heart_rate_trend(self, timestamp_ns: Optional[int] = None) -> TrendType:
        """
        心拍数のトレンド判定を取得（リアルタイム対応）
        
        Args:
            timestamp_ns (Optional[int]): 基準時刻（ナノ秒）。Noneの場合は最新時刻を使用
            
        Returns:
            TrendType: "increasing", "decreasing", "stable" のいずれか
        """
        if timestamp_ns is None:
            # 最新の時刻を取得
            time_range = self.instantaneous_hr.get_time_range()
            if time_range is None:
                return "stable"
            timestamp_ns = time_range[1]  # 最新時刻
        
        # リアルタイム用のトレンド判定を使用
        return self.instantaneous_hr.get_realtime_trend(timestamp_ns)
    
    def get_instantaneous_hr_data(self) -> List[Tuple[int, float]]:
        """
        瞬間心拍数データを取得
        
        Returns:
            List[Tuple[int, float]]: [(timestamp_ns, hr_bpm), ...] の形式
        """
        return self.instantaneous_hr.get_instantaneous_hr()
    
    def get_block_averages(self, window_seconds: Optional[float] = None) -> List[Dict[str, any]]:
        """
        ブロック平均データを取得
        
        Args:
            window_seconds (Optional[float]): ブロックサイズ（秒）、Noneの場合は設定ファイルから取得
            
        Returns:
            List[Dict]: ブロック平均データ
        """
        # ウィンドウサイズを決定（設定ファイルからデフォルト値を取得）
        if window_seconds is None:
            window_seconds = HR_BLOCK_WINDOW_SECONDS
        
        return self.instantaneous_hr.get_block_averages(window_seconds)
    
    def get_detected_beats(self) -> List[BeatEvent]:
        """
        検出されたR波イベントのリストを取得
        
        Returns:
            List[BeatEvent]: 検出されたR波イベントのリスト
        """
        return self.r_peak_detector.detected_peaks
    
    def reset_r_peak_detector(self):
        """R波検出器と瞬間心拍数算出器の状態をリセット"""
        self.r_peak_detector.reset()
        self.instantaneous_hr.reset()
        logger.info("R-peak detector and instantaneous heart rate calculator reset")
    
    def clear_data(self):
        """保存されているECGデータをクリア"""
        self.ecg_data_list.clear()
        
        # R波検出器と瞬間心拍数算出器もリセット
        self.r_peak_detector.reset()
        self.instantaneous_hr.reset()
        
        logger.info("ECG data, R-peak detector, and instantaneous heart rate calculator cleared")
