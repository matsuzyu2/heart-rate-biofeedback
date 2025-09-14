# ECG専用データ処理・解析
from typing import List, Dict, Any, Optional, Callable
import logging

# R波検出器をインポート
from .r_peak_detector import RPeakDetector, BeatEvent
# ECG設定をインポート
from ..config.ecg_config import ECG_SAMPLING_RATE

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
        self.r_peak_detector = RPeakDetector(self.sampling_rate)
        self.beat_callback: Optional[Callable[[BeatEvent], None]] = None
    
    def set_beat_callback(self, callback: Callable[[BeatEvent], None]):
        """
        R波検出時のコールバック関数を設定
        
        Args:
            callback: R波検出時に呼び出される関数
        """
        self.beat_callback = callback
        self.r_peak_detector.set_beat_callback(callback)
    
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
    
    def get_heart_rate_bpm(self, window_duration_ms: int = 10000) -> Optional[float]:
        """
        現在の心拍数を取得
        
        Args:
            window_duration_ms: 計算窓の時間幅（ミリ秒）
            
        Returns:
            Optional[float]: 心拍数（BPM）、計算できない場合はNone
        """
        return self.r_peak_detector.get_heart_rate_bpm(window_duration_ms)
    
    def get_detected_beats(self) -> List[BeatEvent]:
        """
        検出されたR波イベントのリストを取得
        
        Returns:
            List[BeatEvent]: 検出されたR波イベントのリスト
        """
        return self.r_peak_detector.detected_peaks
    
    def reset_r_peak_detector(self):
        """R波検出器の状態をリセット"""
        self.r_peak_detector.reset()
        logger.info("R-peak detector reset")
    
    def clear_data(self):
        """保存されているECGデータをクリア"""
        self.ecg_data_list.clear()
        
        # R波検出器もリセット
        self.r_peak_detector.reset()
        
        logger.info("ECG data and R-peak detector cleared")


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


if __name__ == "__main__":
    main()
