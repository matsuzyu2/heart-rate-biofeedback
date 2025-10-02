"""
InstantaneousHRLoggerクラス - 瞬間心拍数データのCSV保存機能
"""
import csv
import os
from typing import Dict, Any
from datetime import datetime

from ..config.ecg_config import INSTANTANEOUS_HR_LOG_DIRECTORY


class InstantaneousHRLogger:
    """
    瞬間心拍数データをCSVファイルに保存するクラス
    
    既存のECGLogger、BeatEventLoggerと同じ設計パターンを踏襲し、
    単一責任原則に基づいてロギング機能のみを担当します。
    """
    
    # CSVカラム定義（将来的な拡張に備えてクラス定数として定義）
    COLUMNS = ['id', 'timestamp_ns', 'rr_interval_ms', 'instantaneous_hr_bpm']
    
    def __init__(self, file_path: str):
        """
        InstantaneousHRLoggerを初期化
        
        Args:
            file_path (str): 保存先CSVファイルのパス
        """
        self.file_path = file_path
        self._record_id = 0  # 連番IDカウンタ（1から始まる）
        self._initialize_csv_file()
    
    def _initialize_csv_file(self):
        """
        瞬間心拍数用CSVファイルを初期化してヘッダーを書き込む
        """
        # ディレクトリが存在しない場合は作成
        dir_path = os.path.dirname(self.file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # ファイルが存在しない場合のみヘッダーを追加
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 瞬間心拍数データ用ヘッダー
                writer.writerow(self.COLUMNS)
    
    def log_instantaneous_hr(self, instantaneous_hr_data: Dict[str, Any]):
        """
        瞬間心拍数データをCSVファイルに追記保存
        
        Args:
            instantaneous_hr_data (Dict[str, Any]): 瞬間心拍数データ
                必須フィールド: 'timestamp_ns', 'rr_interval_ms', 'instantaneous_hr_bpm'
                
        Raises:
            KeyError: 必須フィールドが欠落している場合
            
        Note:
            連番IDは内部で自動管理され、1から始まり連続して付与されます。
            各セッション（ロガーインスタンス）ごとにリセットされます。
        """
        # 必須フィールドの存在確認
        required_fields = ['timestamp_ns', 'rr_interval_ms', 'instantaneous_hr_bpm']
        for field in required_fields:
            if field not in instantaneous_hr_data:
                raise KeyError(f"'{field}' field is required")
        
        # 連番IDをインクリメント（1から始まる）
        self._record_id += 1
        
        # 各フィールドの値を取得
        timestamp_ns = instantaneous_hr_data['timestamp_ns']
        rr_interval_ms = instantaneous_hr_data['rr_interval_ms']
        instantaneous_hr_bpm = instantaneous_hr_data['instantaneous_hr_bpm']
        
        # 瞬間心拍数データを1行として保存
        with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                self._record_id,
                timestamp_ns,
                rr_interval_ms,
                instantaneous_hr_bpm
            ])


def create_instantaneous_hr_log_filename(base_name: str = "instantaneous_hr_session") -> str:
    """
    瞬間心拍数ログファイル名を生成し、設定ファイルで指定されたディレクトリとの完全パスを返す
    
    Args:
        base_name (str): ベースファイル名
        
    Returns:
        str: 設定ディレクトリを含むタイムスタンプ付きファイルの完全パス
        
    Example:
        >>> create_instantaneous_hr_log_filename()
        'logs/instantaneous_hr/20251002_143022_instantaneous_hr_session.csv'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{base_name}.csv"
    return os.path.join(INSTANTANEOUS_HR_LOG_DIRECTORY, filename)


def main():
    """InstantaneousHRLoggerのテスト用メイン処理"""
    # テスト用ログファイル作成
    test_log_path = create_instantaneous_hr_log_filename("test")
    logger = InstantaneousHRLogger(test_log_path)
    
    # テスト用瞬間心拍数データ
    test_data_list = [
        {
            "timestamp_ns": 1694772000000000000,
            "rr_interval_ms": 750.5,
            "instantaneous_hr_bpm": 79.93
        },
        {
            "timestamp_ns": 1694772000750000000,
            "rr_interval_ms": 800.2,
            "instantaneous_hr_bpm": 74.98
        },
        {
            "timestamp_ns": 1694772001550000000,
            "rr_interval_ms": 720.8,
            "instantaneous_hr_bpm": 83.24
        }
    ]
    
    # 瞬間心拍数データをログ
    for data in test_data_list:
        logger.log_instantaneous_hr(data)
    
    print(f"Instantaneous HR data logged to: {logger.file_path}")
    print(f"Total records: {logger._record_id}")


if __name__ == "__main__":
    main()
