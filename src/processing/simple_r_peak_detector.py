# シンプルなR波検出クラス（動的閾値方式）
# FIXME: R波検出でインデックス一個分ほど間違える場合有り
from typing import List, Optional, Callable
import numpy as np
import logging
from dataclasses import dataclass
from collections import deque

# ECG設定をインポート
from ..config.ecg_config import ECG_SAMPLING_RATE

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BeatEvent:
    """
    検出されたR波イベントの情報
    
    Attributes:
        timestamp_ns (int): R波検出時刻（ナノ秒単位、絶対時刻）
        sample_index (int): サンプルインデックス
        amplitude (float): R波の振幅値
        rr_interval_ms (Optional[float]): 前回のR波からの間隔（ミリ秒単位）
    """
    timestamp_ns: int  # R波検出時刻（ナノ秒、絶対時刻）
    sample_index: int  # サンプルインデックス
    amplitude: float   # R波の振幅値
    rr_interval_ms: Optional[float] = None  # 前回のR波からの間隔（ミリ秒）


class SimpleRPeakDetector:
    """
    動的閾値方式を使用したシンプルなR波検出クラス
    
    アルゴリズム:
    1. スライディングウィンドウで信号の統計情報を追跡
    2. 窓内の最大値・中央値を計算
    3. 閾値 = 中央値 + (最大値 - 中央値) × 0.6
    4. リフラクトリ期間で偽陽性を除去
    """
    
    def __init__(self, sampling_rate: Optional[int] = None):
        """
        R波検出器を初期化
        
        Args:
            sampling_rate (Optional[int]): サンプリング周波数（Hz）
        """
        self.sampling_rate = sampling_rate or ECG_SAMPLING_RATE
        
        # アルゴリズムパラメータ
        self.statistics_window_seconds = 5.0  # 統計窓サイズ（秒）
        self.threshold_coefficient = 0.6  # 閾値係数
        self.refractory_period_ms = 200  # リフラクトリ期間（ミリ秒）
        
        # サンプル数に変換
        self.statistics_window_samples = int(self.statistics_window_seconds * self.sampling_rate)
        self.refractory_period_samples = int(self.refractory_period_ms * self.sampling_rate / 1000)
        
        # 信号バッファ（統計計算用）
        self.signal_buffer = deque(maxlen=self.statistics_window_samples)
        self.timestamp_buffer = deque(maxlen=self.statistics_window_samples)
        
        # 状態変数
        self.sample_count = 0
        self.last_peak_sample = -self.refractory_period_samples
        self.detected_peaks: List[BeatEvent] = []
        
        # 動的閾値
        self.current_threshold = 0.0
        
        # コールバック関数
        self.beat_callback: Optional[Callable[[BeatEvent], None]] = None
        
        logger.info(f"SimpleRPeakDetector初期化: サンプリング周波数={self.sampling_rate}Hz, "
                   f"統計窓={self.statistics_window_seconds}秒, "
                   f"閾値係数={self.threshold_coefficient}")
    
    def set_beat_callback(self, callback: Callable[[BeatEvent], None]):
        """
        R波検出時のコールバック関数を設定
        
        Args:
            callback: R波検出時に呼び出される関数
        """
        self.beat_callback = callback
    
    def add_samples(self, samples: List[float], timestamps: List[int]) -> List[BeatEvent]:
        """
        新しいECGサンプルを追加し、R波を検出
        
        Args:
            samples: ECGサンプル値のリスト
            timestamps: 各サンプルのタイムスタンプ（ナノ秒）
            
        Returns:
            List[BeatEvent]: 検出されたR波イベントのリスト
        """
        if len(samples) != len(timestamps):
            raise ValueError("サンプル数とタイムスタンプ数が一致しません")
        
        detected_beats = []
        
        for sample, timestamp in zip(samples, timestamps):
            self.signal_buffer.append(sample)
            self.timestamp_buffer.append(timestamp)
            self.sample_count += 1
            
            # 動的閾値を更新
            self._update_threshold()
            
            # R波検出をチェック
            beat_event = self._check_r_peak_detection(sample, timestamp)
            if beat_event:
                detected_beats.append(beat_event)
                self.detected_peaks.append(beat_event)
                
                # コールバック呼び出し
                if self.beat_callback:
                    self.beat_callback(beat_event)
        
        return detected_beats
    
    def _update_threshold(self):
        """
        動的閾値を更新
        
        統計窓内の信号から閾値を計算:
        閾値 = 中央値 + (最大値 - 中央値) × 係数
        """
        # 統計窓が満たされていない場合はスキップ
        if len(self.signal_buffer) < min(self.statistics_window_samples, self.sampling_rate):
            # 最低1秒分のデータが必要
            return
        
        # 統計情報を計算
        signal_array = np.array(self.signal_buffer)
        median_value = np.median(signal_array)
        max_value = np.max(signal_array)
        
        # 閾値を計算: 中央値 + (最大値 - 中央値) × 係数
        self.current_threshold = median_value + (max_value - median_value) * self.threshold_coefficient
    
    def _check_r_peak_detection(self, sample: float, timestamp: int) -> Optional[BeatEvent]:
        """
        現在のサンプルがR波かどうかを判定
        
        Args:
            sample: 現在のECGサンプル値
            timestamp: 現在のタイムスタンプ
            
        Returns:
            Optional[BeatEvent]: 検出されたR波イベント（検出されなかった場合はNone）
        """
        # 閾値が設定されていない場合はスキップ
        if self.current_threshold == 0.0:
            return None
        
        # リフラクトリ期間チェック
        if self.sample_count - self.last_peak_sample < self.refractory_period_samples:
            return None
        
        # ピーク検出: 現在のサンプルが閾値を超えているか
        if sample > self.current_threshold:
            # 局所最大値かチェック（前後のサンプルと比較）
            if self._is_local_maximum(sample):
                # R波として検出
                beat_event = self._create_beat_event(sample, timestamp)
                self.last_peak_sample = self.sample_count
                return beat_event
        
        return None
    
    def _is_local_maximum(self, sample: float) -> bool:
        """
        現在のサンプルが局所最大値かどうかを判定
        
        Args:
            sample: 現在のサンプル値
            
        Returns:
            bool: 局所最大値の場合True
        """
        # バッファが十分でない場合は判定不可
        if len(self.signal_buffer) < 3:
            return False
        
        # 現在のサンプルは最後の要素
        # 前のサンプルと比較
        if len(self.signal_buffer) >= 2:
            prev_sample = self.signal_buffer[-2]
            if sample <= prev_sample:
                return False
        
        return True
    
    def _create_beat_event(self, amplitude: float, timestamp: int) -> BeatEvent:
        """
        BeatEventオブジェクトを作成
        
        Args:
            amplitude: R波の振幅
            timestamp: タイムスタンプ
            
        Returns:
            BeatEvent: 作成されたビートイベント
        """
        # RR間隔の計算
        rr_interval_ms = None
        if len(self.detected_peaks) > 0:
            last_beat = self.detected_peaks[-1]
            rr_interval_ns = timestamp - last_beat.timestamp_ns
            rr_interval_ms = rr_interval_ns / 1_000_000  # ナノ秒からミリ秒に変換
        
        return BeatEvent(
            timestamp_ns=timestamp,
            sample_index=self.sample_count,
            amplitude=amplitude,
            rr_interval_ms=rr_interval_ms
        )
    
    def get_heart_rate_bpm(self, window_duration_ms: int = 10000) -> Optional[float]:
        """
        指定された時間窓での心拍数を計算
        
        Args:
            window_duration_ms: 計算窓の時間幅（ミリ秒）
            
        Returns:
            Optional[float]: 心拍数（BPM）、計算できない場合はNone
        """
        if len(self.detected_peaks) < 2:
            return None
        
        # 現在時刻から指定時間窓内のビートを取得
        current_time = self.detected_peaks[-1].timestamp_ns
        window_start_time = current_time - (window_duration_ms * 1_000_000)  # ナノ秒に変換
        
        recent_beats = [
            beat for beat in self.detected_peaks 
            if beat.timestamp_ns >= window_start_time
        ]
        
        if len(recent_beats) < 2:
            return None
        
        # RR間隔の平均から心拍数を計算
        rr_intervals = [
            beat.rr_interval_ms for beat in recent_beats[1:] 
            if beat.rr_interval_ms is not None
        ]
        
        if not rr_intervals:
            return None
        
        avg_rr_interval_ms = np.mean(rr_intervals)
        heart_rate_bpm = 60000.0 / avg_rr_interval_ms  # 60秒 * 1000ms / 平均RR間隔
        
        return heart_rate_bpm
    
    def reset(self):
        """検出器の状態をリセット"""
        self.signal_buffer.clear()
        self.timestamp_buffer.clear()
        self.sample_count = 0
        self.last_peak_sample = -self.refractory_period_samples
        self.detected_peaks.clear()
        self.current_threshold = 0.0
        
        logger.info("SimpleRPeakDetector reset")


def main():
    """SimpleRPeakDetectorのテスト用メイン処理"""
    import math
    
    # テスト用の合成ECG信号を生成
    sampling_rate = ECG_SAMPLING_RATE
    duration = 10  # 10秒
    time_samples = np.arange(0, duration, 1/sampling_rate)
    
    # 60 BPMの心拍数をシミュレート
    heart_rate = 60  # BPM
    rr_interval = 60.0 / heart_rate  # 秒
    
    # 合成ECG信号（簡単なQRS複合波モデル）
    ecg_signal = []
    timestamps = []
    
    for i, t in enumerate(time_samples):
        # ベースライン + ノイズ
        baseline = 0.0
        noise = np.random.normal(0, 0.05)
        
        # QRS複合波の生成（1秒間隔でR波）
        qrs_amplitude = 0.0
        for beat_time in np.arange(0, duration, rr_interval):
            if abs(t - beat_time) < 0.05:  # R波の幅（100ms）
                qrs_amplitude = math.exp(-((t - beat_time) * 20) ** 2)  # ガウシアン様のR波
        
        sample_value = baseline + qrs_amplitude + noise
        ecg_signal.append(sample_value)
        timestamps.append(int(t * 1_000_000_000))  # ナノ秒に変換
    
    # R波検出器を初期化
    detector = SimpleRPeakDetector()
    
    # コールバック関数を設定
    def beat_detected(beat_event: BeatEvent):
        rr_info = f"RR: {beat_event.rr_interval_ms:.1f}ms" if beat_event.rr_interval_ms else "first beat"
        print(f"Beat detected: {beat_event.timestamp_ns / 1_000_000:.1f}ms, {rr_info}")
    
    detector.set_beat_callback(beat_detected)
    
    # ストリーミング処理をシミュレート（10サンプルずつ処理）
    chunk_size = 10
    for i in range(0, len(ecg_signal), chunk_size):
        chunk_samples = ecg_signal[i:i+chunk_size]
        chunk_timestamps = timestamps[i:i+chunk_size]
        
        detected_beats = detector.add_samples(chunk_samples, chunk_timestamps)
    
    # 心拍数を計算
    hr = detector.get_heart_rate_bpm()
    if hr:
        print(f"\n推定心拍数: {hr:.1f} BPM")
    
    # 検出されたビート数を表示
    print(f"検出されたビート数: {len(detector.detected_peaks)}")


if __name__ == "__main__":
    main()
