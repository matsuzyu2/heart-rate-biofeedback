# 瞬間心拍数算出とトレンド判定クラス
from typing import List, Optional, Tuple, Dict, Literal
import numpy as np
import logging

# 既存のBeatEventをインポート
from .simple_r_peak_detector import BeatEvent
from ..config.ecg_config import HR_TREND_THRESHOLD_BPM, HR_BLOCK_WINDOW_SECONDS

# ログ設定
logger = logging.getLogger(__name__)

# 型エイリアス
TrendType = Literal["increasing", "decreasing", "stable"]


class InstantaneousHeartRate:
    """
    RR間隔から瞬間心拍数を算出し、トレンド判定を行うクラス
    
    Attributes:
        trend_threshold_bpm (float): トレンド判定の閾値（BPM単位）
        _instantaneous_hr_data (List[Tuple[int, float]]): 瞬間心拍数の時系列データ
        _max_data_points (int): メモリ管理のためのデータ点数上限
    """
    
    def __init__(self, trend_threshold_bpm: Optional[float] = None):
        """
        瞬間心拍数算出器を初期化
        
        Args:
            trend_threshold_bpm (Optional[float]): トレンド判定の閾値（BPM）
                                                 Noneの場合は設定ファイルから取得
        """
        self.trend_threshold_bpm = trend_threshold_bpm or HR_TREND_THRESHOLD_BPM
        
        # 瞬間心拍数の時系列データ (timestamp_ns, hr_bpm)
        self._instantaneous_hr_data: List[Tuple[int, float]] = []
        
        # 効率的な検索のためのインデックス管理
        self._max_data_points = 10000  # メモリ管理のための上限
    
    def add_beat_event(self, beat: BeatEvent) -> None:
        """
        ビートイベントを追加し、瞬間心拍数を計算
        
        Args:
            beat (BeatEvent): 検出されたビートイベント
        """
        # 最初のビートイベントはスキップ
        if beat.rr_interval_ms is None:
            return
        
        if beat.rr_interval_ms <= 0:
            logger.warning(f"Invalid RR interval: {beat.rr_interval_ms}ms at {beat.timestamp_ns}ns")
            return
        
        # 瞬間心拍数を計算
        instantaneous_hr = 60000.0 / beat.rr_interval_ms
        
        # データを追加
        self._instantaneous_hr_data.append((beat.timestamp_ns, instantaneous_hr))
        
        # メモリ管理: 古いデータを削除
        if len(self._instantaneous_hr_data) > self._max_data_points:
            self._instantaneous_hr_data = self._instantaneous_hr_data[-self._max_data_points//2:]
    
    def get_instantaneous_hr(self) -> List[Tuple[int, float]]:
        """
        すべての瞬間心拍数データを取得
        
        Returns:
            List[Tuple[int, float]]: [(timestamp_ns, hr_bpm), ...] の形式
        """
        return self._instantaneous_hr_data.copy()
    
    def get_block_averages(
        self, 
        window_seconds: float, 
        start_time: Optional[int] = None
    ) -> List[Dict[str, any]]:
        """
        ブロックごとの平均心拍数を計算
        
        Args:
            window_seconds (float): ブロックのサイズ（秒）、必須パラメータ
            start_time (Optional[int]): 開始時刻（ナノ秒）、Noneの場合は最初のデータから
            
        Returns:
            List[Dict]: [{"start_ns": int, "end_ns": int, "average_hr": float}, ...]
                       ビートが含まれないブロックは除外される
        """
        if not self._instantaneous_hr_data:
            return []
        
        # 開始時刻の決定
        if start_time is None:
            start_time = self._instantaneous_hr_data[0][0]
        
        # ナノ秒単位のウィンドウサイズ
        window_ns = int(window_seconds * 1_000_000_000)
        
        # 最終時刻
        end_time = self._instantaneous_hr_data[-1][0]
        
        block_averages = []
        current_start = start_time
        
        while current_start < end_time:
            current_end = current_start + window_ns
            
            # 現在のブロック内のデータを取得
            block_data = [
                hr for timestamp, hr in self._instantaneous_hr_data
                if current_start <= timestamp < current_end
            ]
            
            # ブロックにデータがある場合のみ平均を計算
            if block_data:
                average_hr = np.mean(block_data)
                block_averages.append({
                    "start_ns": current_start,
                    "end_ns": current_end,
                    "average_hr": average_hr
                })
            
            current_start = current_end
        
        return block_averages
    
    def get_trend_at(
        self, 
        timestamp_ns: int, 
        pre_window_s: Optional[float] = None,
        post_window_s: Optional[float] = None,
        threshold_bpm: Optional[float] = None
    ) -> TrendType:
        """
        指定時刻でのトレンド判定を実行
        
        Args:
            timestamp_ns (int): 基準時刻（ナノ秒）
            pre_window_s (Optional[float]): 前ウィンドウの長さ（秒）、Noneの場合は設定ファイルから取得
            post_window_s (Optional[float]): 後ウィンドウの長さ（秒）、Noneの場合は設定ファイルから取得
            threshold_bpm (Optional[float]): 閾値（BPM）、Noneの場合はインスタンス設定を使用
            
        Returns:
            TrendType: "increasing", "decreasing", "stable" のいずれか
        """
        if threshold_bpm is None:
            threshold_bpm = self.trend_threshold_bpm
        
        # ウィンドウサイズの決定（設定ファイルからデフォルト値を取得）
        if pre_window_s is None:
            pre_window_s = HR_BLOCK_WINDOW_SECONDS
        if post_window_s is None:
            post_window_s = HR_BLOCK_WINDOW_SECONDS
        
        # ナノ秒単位に変換
        pre_window_ns = int(pre_window_s * 1_000_000_000)
        post_window_ns = int(post_window_s * 1_000_000_000)
        
        # 前ウィンドウのデータ: (timestamp_ns - pre_window_ns, timestamp_ns]
        pre_window_start = timestamp_ns - pre_window_ns
        pre_data = [
            hr for ts, hr in self._instantaneous_hr_data
            if pre_window_start < ts <= timestamp_ns
        ]
        
        # 後ウィンドウのデータ: (timestamp_ns, timestamp_ns + post_window_ns]
        post_window_end = timestamp_ns + post_window_ns
        post_data = [
            hr for ts, hr in self._instantaneous_hr_data
            if timestamp_ns < ts <= post_window_end
        ]
        
        # データが不十分な場合はstableを返す
        if not pre_data or not post_data:
            logger.info(f"Insufficient data for trend analysis at {timestamp_ns}ns")
            return "stable"
        
        # 各ウィンドウの平均を計算
        pre_average = np.mean(pre_data)
        post_average = np.mean(post_data)
        
        # トレンド判定
        difference = post_average - pre_average
        
        if difference >= threshold_bpm:
            return "increasing"
        elif difference <= -threshold_bpm:
            return "decreasing"
        else:
            return "stable"
    
    def reset(self) -> None:
        """
        すべてのデータをクリアして初期状態に戻す
        """
        self._instantaneous_hr_data.clear()
    
    def get_data_count(self) -> int:
        """
        保持している瞬間心拍数データの数を取得
        
        Returns:
            int: データ点数
        """
        return len(self._instantaneous_hr_data)
    
    def get_time_range(self) -> Optional[Tuple[int, int]]:
        """
        保持しているデータの時間範囲を取得
        
        Returns:
            Optional[Tuple[int, int]]: (最初のタイムスタンプ, 最後のタイムスタンプ) 
                                     データがない場合はNone
        """
        if not self._instantaneous_hr_data:
            return None
        
        return (self._instantaneous_hr_data[0][0], self._instantaneous_hr_data[-1][0])