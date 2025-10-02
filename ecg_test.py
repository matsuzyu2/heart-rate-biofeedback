#!/usr/bin/env python3
"""
ECG動作確認スクリプト
"""
import asyncio
import sys
import logging

# ECG関連モジュールのインポート
from src.sensor.ecg_interface import ECGInterface
from src.processing.ecg_processor import ECGProcessor
from src.processing.ecg_logger import ECGLogger, create_ecg_log_filename, BeatEventLogger, create_beat_log_filename
from src.processing.instantaneous_hr_logger import InstantaneousHRLogger, create_instantaneous_hr_log_filename

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


class ECGTestRunner:
    """
    ECG動作確認テストランナー
    """
    
    def __init__(self):
        """テストランナーの初期化"""
        self.ecg_interface = ECGInterface()
        self.ecg_processor = ECGProcessor()
        self.ecg_logger = None
        self.beat_logger = None
        self.instantaneous_hr_logger = None
    
    def on_ecg_data_received(self, ecg_data):
        """
        ECGデータ受信時のコールバック処理
        
        Args:
            ecg_data: ECGインターフェースから受信したデータ
        """
        if self.ecg_processor.add_ecg_data(ecg_data):
            if self.ecg_logger:
                try:
                    self.ecg_logger.log_ecg_data(ecg_data)
                except Exception as e:
                    logger.error(f"Logging failed: {e}")
    
    async def run_test(self):
        """
        ECG動作確認テストを実行（ユーザー中断まで継続）
        """
        logger.info("=== ECG動作確認テスト開始 ===")
        
        try:
            
            log_path = create_ecg_log_filename("ecg_session")
            self.ecg_logger = ECGLogger(log_path)
            logger.info(f"Log file: {log_path}")
            
            # BeatEventLoggerの初期化
            beat_log_path = create_beat_log_filename("beat_session")
            self.beat_logger = BeatEventLogger(beat_log_path)
            logger.info(f"Beat log file: {beat_log_path}")
            
            # InstantaneousHRLoggerの初期化
            instantaneous_hr_log_path = create_instantaneous_hr_log_filename("instantaneous_hr_session")
            self.instantaneous_hr_logger = InstantaneousHRLogger(instantaneous_hr_log_path)
            logger.info(f"Instantaneous HR log file: {instantaneous_hr_log_path}")
            
            # ECGProcessorにロガーを設定
            self.ecg_processor.set_beat_logger(self.beat_logger)
            self.ecg_processor.set_instantaneous_hr_logger(self.instantaneous_hr_logger)
            
            # ECGインターフェース設定
            self.ecg_interface.set_ecg_callback(self.on_ecg_data_received)
            
            # Polar H10に接続
            if not await self.ecg_interface.connect():
                logger.error("Polar H10への接続に失敗しました")
                return False
            
            # ECGストリーミング開始
            if not await self.ecg_interface.start_ecg_streaming():
                logger.error("ECGストリーミングの開始に失敗しました")
                return False
            
            # ユーザー中断まで継続
            logger.info("ECGデータを取得中... (Ctrl+Cで停止)")
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"テスト実行中にエラーが発生: {e}")
            return False
            
        finally:
            # クリーンアップ
            await self._cleanup()
            # テスト結果表示（必ず実行）
            self._display_test_results()
            
    def _display_test_results(self):
        """テスト結果を表示"""
        logger.info("=== テスト結果 ===")
        
        # セッション要約を取得
        summary = self.ecg_processor.get_session_summary()
        logger.info(f"総サンプル数: {summary.get('total_samples', 0)}")
        logger.info(f"セッション時間: {summary.get('duration_seconds', 0):.2f}秒")
    
    async def _cleanup(self):
        """リソースのクリーンアップ"""
        try:
            if self.ecg_interface.is_streaming:
                await self.ecg_interface.stop_ecg_streaming()
            
            if self.ecg_interface.is_connected:
                await self.ecg_interface.disconnect()
                
        except Exception as e:
            logger.error(f"クリーンアップ中にエラー: {e}")


async def main():
    """メイン処理"""
    print("ECG動作確認スクリプト")
    print("Ctrl+Cで中断できます")
    
    # テスト実行
    test_runner = ECGTestRunner()
    
    try:
        success = await test_runner.run_test()
        
        if success:
            print("テストが正常に完了しました")
            sys.exit(0)
        else:
            print("テストが失敗しました")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nテストが中断されました")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
