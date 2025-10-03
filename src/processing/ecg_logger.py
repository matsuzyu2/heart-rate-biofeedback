"""
ECGLoggerクラス - ECGデータのCSV保存機能
"""
import csv
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..config.ecg_config import ECG_LOG_DIRECTORY, BEAT_LOG_DIRECTORY


class ECGLogger:
    """
    ECGデータをCSVファイルに保存するクラス
    
    使用方法:
       logger = ECGLogger()  # ecg_config.ECG_LOG_DIRECTORYを使用
       logger.start_session()
       logger.log_ecg(ecg_data)
       logger.end_session()
    
    Note:
        保存先ディレクトリはecg_config.ECG_LOG_DIRECTORYで設定されます。
        セッション管理パターンのみをサポートし、シンプルで一貫した使用方法を提供します。
    """
    
    def __init__(self):
        """
        ECGLoggerを初期化
        
        Note:
            出力ディレクトリはecg_config.ECG_LOG_DIRECTORYから自動的に取得されます。
        """
        self.output_dir = ECG_LOG_DIRECTORY
        self.file_path: Optional[str] = None
        self._session_started = False
    
    def start_session(self) -> str:
        """
        セッションを開始し、タイムスタンプ付きファイル名を生成
        
        Returns:
            str: 生成されたファイルパス
            
        Raises:
            RuntimeError: セッションが既に開始されている場合
        """
        if self._session_started:
            raise RuntimeError("Session already started")
        
        # タイムスタンプ付きファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_ecg_session.csv"
        self.file_path = os.path.join(self.output_dir, filename)
        
        # CSVファイルを初期化
        self._initialize_csv_file()
        self._session_started = True
        
        return self.file_path
    
    def end_session(self) -> None:
        """
        セッションを終了
        
        Note:
            現在は特別な処理はありませんが、将来的な拡張のために用意
            （例: バッファのフラッシュ、統計情報の出力など）
        """
        if not self._session_started:
            return
        
        self._session_started = False
        # 将来的にクリーンアップ処理を追加する場合はここに記述
    
    def get_filename(self) -> str:
        """
        現在のログファイル名を取得
        
        Returns:
            str: ログファイルのパス
            
        Raises:
            RuntimeError: セッションが開始されていない場合
        """
        if self.file_path is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        return self.file_path
    
    def _initialize_csv_file(self):
        """
        ECG用CSVファイルを初期化してヘッダーを書き込む
        """
        # ディレクトリが存在しない場合は作成
        dir_path = os.path.dirname(self.file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # ファイルが存在しない場合のみヘッダーを追加
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # ECGデータ用ヘッダー
                writer.writerow([
                    'timestamp_ns',
                    'ecg_value_μv'  # マイクロボルト単位のECGサンプル
                ])
    
    def log_ecg_data(self, ecg_data: Dict[str, Any]):
        """
        ECGデータをCSVファイルに追記保存
        
        Args:
            ecg_data (Dict[str, Any]): ECGデータ
                必須フィールド: 'ecg_samples', 'timestamps'
                
        Raises:
            KeyError: 必須フィールドが欠落している場合
            ValueError: データ長が一致しない場合
        """
        # 必須フィールドの存在確認
        required_fields = ['ecg_samples', 'timestamps']
        for field in required_fields:
            if field not in ecg_data:
                raise KeyError(f"'{field}' field is required")
        
        ecg_samples = ecg_data['ecg_samples']
        timestamps = ecg_data['timestamps']
        
        # データ長の整合性確認
        if len(ecg_samples) != len(timestamps):
            raise ValueError(f"Length mismatch: ecg_samples({len(ecg_samples)}) != timestamps({len(timestamps)})")
        
        # 各ECGサンプルを個別行として保存
        with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for ecg_value, timestamp_ns in zip(ecg_samples, timestamps):
                writer.writerow([
                    timestamp_ns,
                    ecg_value
                ])
    
    def log_multiple_ecg_data(self, ecg_data_list: List[Dict[str, Any]]):
        """
        複数のECGデータを一括でCSVファイルに追記保存
        
        Args:
            ecg_data_list (List[Dict[str, Any]]): ECGデータのリスト
        """
        for ecg_data in ecg_data_list:
            self.log_ecg_data(ecg_data)
    
    def log_ecg(self, ecg_data: Dict[str, Any]):
        """
        ECGデータをCSVファイルに追記保存（log_ecg_dataのエイリアス）
        
        Args:
            ecg_data (Dict[str, Any]): ECGデータ
                必須フィールド: 'ecg_samples', 'timestamps'
        
        Note:
            ecg_session_controller.pyとの互換性のために追加されたエイリアスメソッド
        """
        self.log_ecg_data(ecg_data)


class BeatEventLogger:
    """
    BeatEventデータをCSVファイルに保存するクラス
    
    使用方法:
       logger = BeatEventLogger()  # ecg_config.BEAT_LOG_DIRECTORYを使用
       logger.start_session()
       logger.log_beat(beat_data)
       logger.end_session()
    
    Note:
        保存先ディレクトリはecg_config.BEAT_LOG_DIRECTORYで設定されます。
        セッション管理パターンのみをサポートし、シンプルで一貫した使用方法を提供します。
    """
    
    # CSVカラム定義（将来的な拡張に備えてクラス定数として定義）
    COLUMNS = ['timestamp_ns', 'sample_index', 'amplitude', 'rr_interval_ms']
    
    def __init__(self):
        """
        BeatEventLoggerを初期化
        
        Note:
            出力ディレクトリはecg_config.BEAT_LOG_DIRECTORYから自動的に取得されます。
        """
        self.output_dir = BEAT_LOG_DIRECTORY
        self.file_path: Optional[str] = None
        self._session_started = False
    
    def _initialize_csv_file(self):
        """
        BeatEvent用CSVファイルを初期化してヘッダーを書き込む
        """
        # ディレクトリが存在しない場合は作成
        dir_path = os.path.dirname(self.file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # ファイルが存在しない場合のみヘッダーを追加
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # BeatEventデータ用ヘッダー
                writer.writerow(self.COLUMNS)
    
    def start_session(self) -> str:
        """
        セッションを開始し、タイムスタンプ付きファイル名を生成
        
        Returns:
            str: 生成されたファイルパス
            
        Raises:
            RuntimeError: セッションが既に開始されている場合
        """
        if self._session_started:
            raise RuntimeError("Session already started")
        
        # タイムスタンプ付きファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_beat_session.csv"
        self.file_path = os.path.join(self.output_dir, filename)
        
        # CSVファイルを初期化
        self._initialize_csv_file()
        self._session_started = True
        
        return self.file_path
    
    def end_session(self) -> None:
        """
        セッションを終了
        
        Note:
            現在は特別な処理はありませんが、将来的な拡張のために用意
            （例: バッファのフラッシュ、統計情報の出力など）
        """
        if not self._session_started:
            return
        
        self._session_started = False
        # 将来的にクリーンアップ処理を追加する場合はここに記述
    
    def get_filename(self) -> str:
        """
        現在のログファイル名を取得
        
        Returns:
            str: ログファイルのパス
            
        Raises:
            RuntimeError: セッションが開始されていない場合
        """
        if self.file_path is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        return self.file_path
    
    def log_beat(self, beat_event: Dict[str, Any]):
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


def create_ecg_log_filename(base_name: str = "ecg_session") -> str:
    """
    ECGログファイル名を生成し、設定ファイルで指定されたディレクトリとの完全パスを返す
    
    Args:
        base_name (str): ベースファイル名
        
    Returns:
        str: 設定ディレクトリを含むタイムスタンプ付きファイルの完全パス
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{base_name}.csv"
    return os.path.join(ECG_LOG_DIRECTORY, filename)


def create_beat_log_filename(base_name: str = "beat_session") -> str:
    """
    BeatEventログファイル名を生成し、設定ファイルで指定されたディレクトリとの完全パスを返す
    
    Args:
        base_name (str): ベースファイル名
        
    Returns:
        str: 設定ディレクトリを含むタイムスタンプ付きファイルの完全パス
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{base_name}.csv"
    return os.path.join(BEAT_LOG_DIRECTORY, filename)


def main():
    """ECGLoggerのテスト用メイン処理"""
    # ECGLoggerのテスト
    logger = ECGLogger()
    logger.start_session()
    
    # テスト用ECGデータ
    test_ecg_data = {
        "ecg_samples": [0.1, 0.15, 0.2, 0.18, 0.12],
        "timestamps": [1694772000000000000, 1694772000007692307, 1694772000015384615, 1694772000023076923, 1694772000030769230]
    }
    
    # ECGデータをログ
    logger.log_ecg_data(test_ecg_data)
    print(f"ECG data logged to: {logger.get_filename()}")
    
    logger.end_session()
    
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
