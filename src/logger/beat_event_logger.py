"""
BeatEventLoggerクラス - 心拍イベント(R-peak)データのCSV保存機能
"""
import csv
from typing import Dict, Any, List

from .base_logger import BaseSessionLogger
from ..config.ecg_config import BEAT_LOG_DIRECTORY


class BeatEventLogger(BaseSessionLogger):
    """
    BeatEventデータをCSVファイルに保存するクラス
    
    心拍検出アルゴリズムによって検出されたR-peakイベントを記録します。
    BaseSessionLoggerを継承し、統一されたセッション管理APIを提供します。
    
    CSVフォーマット:
        timestamp_ns: R-peak検出時刻（ナノ秒）
        sample_index: サンプルインデックス
        amplitude: R-peakの振幅値
        rr_interval_ms: 前回のR-peakからの間隔（ミリ秒、任意）
    """
    
    # CSVカラム定義
    COLUMNS = ['timestamp_ns', 'sample_index', 'amplitude', 'rr_interval_ms']
    
    def _get_log_directory(self) -> str:
        """
        ログディレクトリのパスを返す
        
        Returns:
            str: BEAT_LOG_DIRECTORYのパス
        """
        return BEAT_LOG_DIRECTORY
    
    def _get_file_prefix(self) -> str:
        """
        ファイル名のプレフィックスを返す
        
        Returns:
            str: "beat"
        """
        return "beat"
    
    def _get_csv_columns(self) -> List[str]:
        """
        CSVのカラム名リストを返す
        
        Returns:
            List[str]: BeatEventデータのカラム名
        """
        return self.COLUMNS
    
    def log_beat(self, beat_event: Dict[str, Any]) -> None:
        """
        BeatEventデータをCSVファイルに追記保存
        
        Args:
            beat_event (Dict[str, Any]): BeatEventデータ
                必須フィールド: 'timestamp_ns', 'sample_index', 'amplitude'
                任意フィールド: 'rr_interval_ms'
                
        Raises:
            KeyError: 必須フィールドが欠落している場合
        """
        # 必須フィールドの存在確認
        required_fields = ['timestamp_ns', 'sample_index', 'amplitude']
        for field in required_fields:
            if field not in beat_event:
                raise KeyError(f"'{field}' field is required")
        
        # 各フィールドの値を取得（任意フィールドはNoneの場合は空文字）
        timestamp_ns = beat_event['timestamp_ns']
        sample_index = beat_event['sample_index']
        amplitude = beat_event['amplitude']
        rr_interval_ms = beat_event.get('rr_interval_ms', '')  # 任意フィールド
        
        # BeatEventデータを1行として保存
        with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp_ns,
                sample_index,
                amplitude,
                rr_interval_ms
            ])


def main():
    """BeatEventLoggerのテスト用メイン処理"""
    # BeatEventLoggerのテスト
    beat_logger = BeatEventLogger()
    beat_logger.start_session()
    
    # テスト用BeatEventデータ
    test_beat_event = {
        "timestamp_ns": 1694772000000000000,
        "sample_index": 1000,
        "amplitude": 0.85,
        "rr_interval_ms": 750.5
    }
    
    # BeatEventデータをログ
    beat_logger.log_beat(test_beat_event)
    print(f"Beat event data logged to: {beat_logger.get_filename()}")
    
    # rr_interval_msが無い場合のテスト
    test_beat_event_no_rr = {
        "timestamp_ns": 1694772000750000000,
        "sample_index": 1098,
        "amplitude": 0.92
    }
    
    beat_logger.log_beat(test_beat_event_no_rr)
    print("Beat event data (without RR interval) logged successfully")
    
    beat_logger.end_session()


if __name__ == "__main__":
    main()
