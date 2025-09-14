# R波検出専用クラス（Pan-Tompkinsアルゴリズム実装）
from typing import List, Optional, Callable, Dict, Any
import numpy as np
from scipy import signal
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
        timestamp_ns (int): R波検出時刻（ナノ秒単位、セッション開始からの相対時間）
        sample_index (int): サンプルインデックス
        amplitude (float): R波の振幅値
        rr_interval_ms (Optional[float]): 前回のR波からの間隔（ミリ秒単位）
    """
    timestamp_ns: int  # R波検出時刻（ナノ秒、セッション開始からの相対時間）
    sample_index: int  # サンプルインデックス
    amplitude: float   # R波の振幅値
    rr_interval_ms: Optional[float] = None  # 前回のR波からの間隔（ミリ秒）


class RPeakDetector:
    """
    Pan-Tompkinsアルゴリズムを使用したリアルタイムR波検出クラス
    
    特徴：
    - 適応的閾値（信号統計に基づく自動調整）
    - ストリーミング対応（バッファ管理）
    - コールバック機能
    - ノイズ耐性
    """
    
    def __init__(self, sampling_rate: Optional[int] = None):
        """
        R波検出器を初期化
        
        Args:
            sampling_rate (Optional[int]): サンプリング周波数（Hz）
        """
        self.sampling_rate = sampling_rate or ECG_SAMPLING_RATE
        
        # Pan-Tompkinsアルゴリズムのパラメータ
        self.lowcut = 5.0    # バンドパスフィルタ下限（Hz）
        self.highcut = 15.0  # バンドパスフィルタ上限（Hz）
        self.integration_window = int(0.15 * self.sampling_rate)  # 移動積分窓サイズ（150ms）
        
        # 適応的閾値パラメータ
        self.peak_threshold_ratio = 0.25  # ピーク検出閾値比率
        self.noise_threshold_ratio = 0.125  # ノイズ閾値比率
        
        # リフラクトリ期間（生理学的制約）
        self.refractory_period_samples = int(0.2 * self.sampling_rate)  # 200ms
        
        # フィルタの初期化
        self._init_filters()
        
        # 状態変数
        self.sample_buffer = deque(maxlen=self.sampling_rate * 2)  # 2秒分のバッファ
        self.timestamp_buffer = deque(maxlen=self.sampling_rate * 2)
        self.sample_count = 0
        
        # 検出状態
        self.last_peak_sample = -self.refractory_period_samples
        self.detected_peaks: List[BeatEvent] = []
        
        # 適応的閾値管理
        self.signal_peak_history = deque(maxlen=8)  # 過去8つのピーク値
        self.noise_peak_history = deque(maxlen=8)   # 過去8つのノイズピーク値
        self.current_signal_threshold = 0.0
        self.current_noise_threshold = 0.0
        
        # コールバック関数
        self.beat_callback: Optional[Callable[[BeatEvent], None]] = None
    
    def _init_filters(self):
        """Pan-Tompkinsアルゴリズムのフィルタを初期化"""
        # バンドパスフィルタ（5-15Hz）
        nyquist = 0.5 * self.sampling_rate
        low = self.lowcut / nyquist
        high = self.highcut / nyquist
        
        # Butterworthフィルタ（4次）
        self.b_band, self.a_band = signal.butter(4, [low, high], btype='band')
        
        # フィルタ状態の初期化
        self.zi_band = signal.lfilter_zi(self.b_band, self.a_band)
        
        # 微分フィルタ（差分近似）
        self.derivative_filter = np.array([-1, -2, 0, 2, 1]) / 8.0
        self.derivative_buffer = deque(maxlen=5)
        
        # 移動積分バッファ
        self.integration_buffer = deque(maxlen=self.integration_window)
    
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
            self.sample_buffer.append(sample)
            self.timestamp_buffer.append(timestamp)
            self.sample_count += 1
            
            # Pan-Tompkinsアルゴリズムを適用
            processed_value = self._apply_pan_tompkins(sample)
            
            if processed_value is not None:
                # R波検出をチェック
                beat_event = self._check_r_peak_detection(processed_value, timestamp)
                if beat_event:
                    detected_beats.append(beat_event)
                    self.detected_peaks.append(beat_event)
                    
                    # コールバック呼び出し
                    if self.beat_callback:
                        self.beat_callback(beat_event)
        
        return detected_beats
    
    def _apply_pan_tompkins(self, sample: float) -> Optional[float]:
        """
        Pan-Tompkinsアルゴリズムの信号処理ステップを適用
        
        Args:
            sample: 入力ECGサンプル
            
        Returns:
            Optional[float]: 処理済み信号値（バッファが不足している場合はNone）
        """
        # 1. バンドパスフィルタ（5-15Hz）
        filtered_sample, self.zi_band = signal.lfilter(
            self.b_band, self.a_band, [sample], zi=self.zi_band
        )
        filtered_value = filtered_sample[0]
        
        # 2. 微分フィルタ
        self.derivative_buffer.append(filtered_value)
        if len(self.derivative_buffer) < 5:
            return None
        
        derivative_value = np.convolve(
            list(self.derivative_buffer), self.derivative_filter, mode='valid'
        )[0]
        
        # 3. 二乗
        squared_value = derivative_value ** 2
        
        # 4. 移動積分
        self.integration_buffer.append(squared_value)
        if len(self.integration_buffer) < self.integration_window:
            return None
        
        integrated_value = np.mean(self.integration_buffer)
        
        return integrated_value
    
    def _check_r_peak_detection(self, processed_value: float, timestamp: int) -> Optional[BeatEvent]:
        """
        処理済み信号からR波を検出
        
        Args:
            processed_value: Pan-Tompkins処理済みの信号値
            timestamp: 現在のタイムスタンプ
            
        Returns:
            Optional[BeatEvent]: 検出されたR波イベント（検出されなかった場合はNone）
        """
        # リフラクトリ期間チェック
        if self.sample_count - self.last_peak_sample < self.refractory_period_samples:
            return None
        
        # 適応的閾値の更新
        self._update_adaptive_thresholds(processed_value)
        
        # ピーク検出
        if processed_value > self.current_signal_threshold:
            # R波として検出
            beat_event = self._create_beat_event(processed_value, timestamp)
            self.last_peak_sample = self.sample_count
            
            # 信号ピーク履歴を更新
            self.signal_peak_history.append(processed_value)
            
            return beat_event
        
        elif processed_value > self.current_noise_threshold:
            # ノイズピークとして記録
            self.noise_peak_history.append(processed_value)
        
        return None
    
    def _update_adaptive_thresholds(self, current_value: float):
        """
        適応的閾値を更新（Pan-Tompkinsアルゴリズムの核心部分）
        """
        if len(self.signal_peak_history) > 0:
            avg_signal_peak = np.mean(self.signal_peak_history)
            self.current_signal_threshold = avg_signal_peak * self.peak_threshold_ratio
        
        if len(self.noise_peak_history) > 0:
            avg_noise_peak = np.mean(self.noise_peak_history)
            self.current_noise_threshold = avg_noise_peak * self.noise_threshold_ratio
        
        # 最小閾値の設定（初期化期間）
        if self.current_signal_threshold == 0:
            self.current_signal_threshold = current_value * 0.25
        if self.current_noise_threshold == 0:
            self.current_noise_threshold = current_value * 0.125
    
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
            
        Note:
            - 計算に用いるtimestamp単位: ナノ秒（BeatEvent.timestamp_ns）
            - ウィンドウの扱い: 閉区間 [current_time - window_duration_ms, current_time]
            - 最新のR波から過去に遡って指定時間窓内のビートを対象とする
            - RR間隔の平均値から心拍数を算出（60000ms / 平均RR間隔ms）
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
        self.sample_buffer.clear()
        self.timestamp_buffer.clear()
        self.sample_count = 0
        self.last_peak_sample = -self.refractory_period_samples
        self.detected_peaks.clear()
        self.signal_peak_history.clear()
        self.noise_peak_history.clear()
        self.current_signal_threshold = 0.0
        self.current_noise_threshold = 0.0
        
        # フィルタ状態もリセット
        self._init_filters()
        
        logger.info("R-peak detector reset")


def main():
    """RPeakDetectorのテスト用メイン処理"""
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
    detector = RPeakDetector()
    
    # コールバック関数を設定
    def beat_detected(beat_event: BeatEvent):
        print(f"Beat detected: {beat_event.timestamp_ns / 1_000_000:.1f}ms, "
              f"RR: {beat_event.rr_interval_ms:.1f}ms" if beat_event.rr_interval_ms else "first beat")
    
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
        print(f"推定心拍数: {hr:.1f} BPM")


if __name__ == "__main__":
    main()