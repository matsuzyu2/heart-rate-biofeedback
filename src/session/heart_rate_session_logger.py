"""
HeartRateSessionLoggerクラス - セッション管理とDataLoggerのラッパー
単一責任原則: セッション情報の管理とファイル名生成を責務とする
DataLoggerを内部で利用してCSV保存機能を実現
簡素化されたAPI: タイムスタンプ+連番の自動ファイル名生成
"""
import os
import glob
from datetime import datetime
from typing import Dict, Any, Optional

from ..processing.data_logger import DataLogger


class HeartRateSessionLogger:
    """
    セッション単位での心拍データロガー
    
    責務:
    - セッション情報の管理
    - タイムスタンプ+連番のファイル名自動生成
    - DataLoggerのラッパー機能
    """
    
    def __init__(self, output_dir: str, session_info: Optional[Dict[str, str]] = None):
        """
        セッションロガーを初期化
        
        Args:
            output_dir (str): 出力ディレクトリのパス
            session_info (Optional[Dict[str, str]]): セッション情報（後方互換性のため保持）
        """
        self.output_dir = output_dir
        self.session_info = session_info or {}
        self.data_logger: Optional[DataLogger] = None
        self._filename: Optional[str] = None
        
        # 出力ディレクトリを作成
        os.makedirs(output_dir, exist_ok=True)
    
    def start_session(self):
        """
        セッションを開始してログファイルを初期化
        """
        # ファイル名を生成
        self._filename = self._generate_filename()
        
        # DataLoggerを初期化
        file_path = os.path.join(self.output_dir, self._filename)
        self.data_logger = DataLogger(file_path)
    
    def log_heart_rate(self, heart_rate_data: Dict[str, Any]):
        """
        心拍データを保存（DataLoggerへの委譲）
        
        Args:
            heart_rate_data (Dict[str, Any]): 心拍データ
        
        Raises:
            RuntimeError: セッションが開始されていない場合
        """
        if self.data_logger is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        
        self.data_logger.log_heart_rate(heart_rate_data)
    
    def end_session(self):
        """
        セッションを終了
        ファイルクローズなどのクリーンアップは不要（ファイルは自動的にクローズされる）
        """
        # 現在のシンプルな実装では特別な処理は不要
        # 将来的にはここでサマリー情報の保存なども可能
        pass
    
    def get_filename(self) -> str:
        """
        生成されたファイル名を取得
        
        Returns:
            str: ファイル名
            
        Raises:
            RuntimeError: セッションが開始されていない場合
        """
        if self._filename is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        return self._filename
    
    def _generate_filename(self) -> str:
        """
        タイムスタンプ+連番から一意のファイル名を生成
        
        Returns:
            str: 生成されたファイル名（例: 20240901_143022_session_001.csv）
        """
        # タイムスタンプを生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 既存ファイルから次の連番を決定
        pattern = os.path.join(self.output_dir, f"{timestamp}_session_*.csv")
        existing_files = glob.glob(pattern)
        
        if not existing_files:
            # 該当するファイルがない場合は001から開始
            sequence_number = 1
        else:
            # 既存ファイルから最大の連番を取得
            max_number = 0
            for file_path in existing_files:
                filename = os.path.basename(file_path)
                try:
                    # ファイル名から連番部分を抽出
                    # 例: 20240901_143022_session_003.csv -> 003
                    number_part = filename.split('_')[-1].replace('.csv', '')
                    number = int(number_part)
                    max_number = max(max_number, number)
                except (ValueError, IndexError):
                    # 予期しないファイル名形式の場合は無視
                    continue
            
            sequence_number = max_number + 1
        
        # ファイル名を組み立て（連番は3桁でゼロパディング）
        return f"{timestamp}_session_{sequence_number:03d}.csv"
