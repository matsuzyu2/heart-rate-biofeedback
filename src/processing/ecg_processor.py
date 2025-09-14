# ECG専用データ処理・解析（ミリボルト単位対応）
from typing import List, Dict, Any
import logging

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
    """
    
    def __init__(self):
        """ECGプロセッサーの初期化"""
        self.ecg_data_list: List[Dict[str, Any]] = []
        self.validator = ECGDataValidator()
    
    def add_ecg_data(self, ecg_data):
        """
        ECGデータを追加
        
        Args:
            ecg_data: 追加するECGデータ
            
        Returns:
            bool: 追加に成功した場合True
        """
        if not self.validator.is_valid_ecg_data(ecg_data):
            return False
            
        self.ecg_data_list.append(ecg_data)
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
    
    def clear_data(self):
        """保存されているECGデータをクリア"""
        self.ecg_data_list.clear()
        logger.info("ECG data cleared")


def main():
    """ECGプロセッサーのテスト用メイン処理"""
    processor = ECGProcessor()
    
    # テスト用のダミーECGデータ
    test_ecg_data = {
        "ecg_samples": [100, 150, 200, 180, 120, 90, 110],  # 24bit符号付き整数
        "timestamps": [1000000000, 1007692307, 1015384615, 1023076923, 1030769230, 1038461538, 1046153846]  # ナノ秒単位
    }
    
    # ECGデータを追加
    success = processor.add_ecg_data(test_ecg_data)
    print(f"ECG data added: {success}")
    
    # セッション要約を取得
    summary = processor.get_session_summary()
    print(f"Session summary: {summary}")


if __name__ == "__main__":
    main()
