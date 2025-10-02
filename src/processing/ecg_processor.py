# ECG専用データ処理・解析
from typing import List, Dict, Any, Optional, Callable, Tuple
import logging

# R波検出器をインポート
from .simple_r_peak_detector import SimpleRPeakDetector, BeatEvent
# 瞬間心拍数算出クラスをインポート
from .instantaneous_heart_rate import InstantaneousHeartRate, TrendType
# ロガークラスをインポート
from .ecg_logger import BeatEventLogger
from .instantaneous_hr_logger import InstantaneousHRLogger
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
        
        self.beat_callback: Optional[Callable[[BeatEvent], None]] = None
        
        # ロガーの初期化（オプション）
        self.beat_logger: Optional[BeatEventLogger] = None
        self.instantaneous_hr_logger: Optional[InstantaneousHRLogger] = None
        
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
        
        # BeatEventLoggerがあればロギング処理を実行
        if self.beat_logger:
            try:
                # BeatEventを辞書形式に変換してロギング
                beat_data = {
                    "timestamp_ns": beat_event.timestamp_ns,
                    "sample_index": beat_event.sample_index,
                    "amplitude": beat_event.amplitude,
                    "rr_interval_ms": beat_event.rr_interval_ms
                }
                self.beat_logger.log_beat(beat_data)
            except Exception as e:
                logger.error(f"Beat event logging failed: {e}")
        
        # InstantaneousHRLoggerがあれば瞬間心拍数をロギング
        # RR間隔が有効な場合のみログ出力（最初のビートはスキップ）
        if self.instantaneous_hr_logger and beat_event.rr_interval_ms is not None:
            try:
                # 瞬間心拍数を計算
                instantaneous_hr_bpm = 60000.0 / beat_event.rr_interval_ms
                
                # 瞬間心拍数データを辞書形式に変換してロギング
                instantaneous_hr_data = {
                    "timestamp_ns": beat_event.timestamp_ns,
                    "rr_interval_ms": beat_event.rr_interval_ms,
                    "instantaneous_hr_bpm": instantaneous_hr_bpm
                }
                self.instantaneous_hr_logger.log_instantaneous_hr(instantaneous_hr_data)
            except Exception as e:
                logger.error(f"Instantaneous HR logging failed: {e}")
        
        # 外部コールバックがあれば実行
        if self.beat_callback:
            self.beat_callback(beat_event)
    
    def set_beat_callback(self, callback: Callable[[BeatEvent], None]):
        """
        R波検出時のコールバック関数を設定
        
        Args:
            callback: R波検出時に呼び出される関数
        """
        self.beat_callback = callback
    
    def set_beat_logger(self, beat_logger: BeatEventLogger):
        """
        BeatEventLoggerを設定
        
        Args:
            beat_logger: BeatEventデータをロギングするLogger
        """
        self.beat_logger = beat_logger
    
    def set_instantaneous_hr_logger(self, instantaneous_hr_logger: InstantaneousHRLogger):
        """
        InstantaneousHRLoggerを設定
        
        Args:
            instantaneous_hr_logger: 瞬間心拍数データをロギングするLogger
        """
        self.instantaneous_hr_logger = instantaneous_hr_logger
    
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
        
        if not block_averages:
            # フォールバック: 従来のRPeakDetectorを使用
            fallback_window_ms = window_duration_ms or int(HR_BLOCK_WINDOW_SECONDS * 1000)
            return self.r_peak_detector.get_heart_rate_bpm(fallback_window_ms)
        
        # 最新のブロック平均を返す
        latest_block = block_averages[-1]
        return latest_block["average_hr"]
    
    def get_heart_rate_trend(self, timestamp_ns: Optional[int] = None) -> TrendType:
        """
        心拍数のトレンド判定を取得
        
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
        
        return self.instantaneous_hr.get_trend_at(timestamp_ns)
    
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


def main():
    """ECGプロセッサーのテスト用メイン処理"""
    processor = ECGProcessor()
    
    # R波検出コールバックを設定
    def on_beat_detected(beat_event: BeatEvent):
        rr_info = f", RR: {beat_event.rr_interval_ms:.1f}ms" if beat_event.rr_interval_ms else ""
        print(f"Beat detected at {beat_event.timestamp_ns / 1_000_000:.1f}ms{rr_info}")
    
    processor.set_beat_callback(on_beat_detected)
    
    # テスト用のダミーECGデータ（複数のチャンク）
    import numpy as np
    
    # 合成ECG信号を生成（60 BPMをシミュレート）
    sampling_rate = ECG_SAMPLING_RATE
    chunk_duration = 1.0  # 1秒のチャンク
    samples_per_chunk = int(sampling_rate * chunk_duration)
    
    for chunk_idx in range(5):  # 5秒分のデータを処理
        time_offset = chunk_idx * chunk_duration
        time_samples = np.linspace(time_offset, time_offset + chunk_duration, samples_per_chunk)
        
        # 簡単な合成ECG信号
        ecg_samples = []
        timestamps = []
        
        for i, t in enumerate(time_samples):
            # 1秒間隔でR波を生成
            qrs_amplitude = 0.0
            if abs(t % 1.0 - 0.5) < 0.05:  # 0.5秒付近でR波
                qrs_amplitude = np.exp(-((t % 1.0 - 0.5) * 20) ** 2)
            
            # ノイズ + R波
            sample_value = qrs_amplitude + np.random.normal(0, 0.02)
            ecg_samples.append(sample_value)
            timestamps.append(int(t * 1_000_000_000))  # ナノ秒
        
        test_ecg_data = {
            "ecg_samples": ecg_samples,
            "timestamps": timestamps
        }
        
        # ECGデータを追加（R波検出も実行される）
        success = processor.add_ecg_data(test_ecg_data)
        print(f"Chunk {chunk_idx + 1} added: {success}")
    
    # セッション要約を取得
    summary = processor.get_session_summary()
    print(f"\nSession summary: {summary}")
    
    # 心拍数を取得
    heart_rate = processor.get_heart_rate_bpm()
    if heart_rate:
        print(f"Current heart rate: {heart_rate:.1f} BPM")
    else:
        print("Heart rate calculation not available")
    
    # トレンド判定を取得
    trend = processor.get_heart_rate_trend()
    print(f"Heart rate trend: {trend}")
    
    # 瞬間心拍数データの統計を表示
    hr_data = processor.get_instantaneous_hr_data()
    if hr_data:
        hr_values = [hr for _, hr in hr_data]
        print(f"Instantaneous HR data points: {len(hr_values)}")
        print(f"HR range: {min(hr_values):.1f} - {max(hr_values):.1f} BPM")
    
    # ブロック平均を表示
    block_averages = processor.get_block_averages()
    if block_averages:
        print(f"Block averages ({len(block_averages)} blocks):")
        for i, block in enumerate(block_averages):
            start_s = block["start_ns"] / 1_000_000_000
            end_s = block["end_ns"] / 1_000_000_000
            print(f"  Block {i+1}: {start_s:.1f}-{end_s:.1f}s, HR: {block['average_hr']:.1f} BPM")


if __name__ == "__main__":
    main()
