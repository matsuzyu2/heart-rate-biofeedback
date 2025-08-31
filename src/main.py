"""
心拍バイオフィードバック実験プログラム - メインアプリケーション
使用例:
    python src/main.py --mode increase    # 心拍数増加報酬モード
    python src/main.py --mode decrease    # 心拍数減少報酬モード
    python src/main.py --mode random      # ランダムモード

"""
import asyncio
import argparse
import signal
import logging
import sys
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.session.session_controller import SessionController
from src.feedback.audio_feedback import AudioFeedback
from src.feedback.feedback_modes import IncreaseRewardMode, DecreaseRewardMode, RandomMode

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('heart_rate_session.log')
    ]
)
logger = logging.getLogger(__name__)


class HeartRateBiofeedbackApp:
    """
    心拍バイオフィードバックアプリケーションクラス
    
    責任:
    - アプリケーションの初期化
    - コマンドライン引数の処理
    - SessionControllerの管理
    - シグナルハンドリング
    """
    
    def __init__(self):
        """アプリケーションの初期化"""
        self.session_controller = None
        self.shutdown_event = asyncio.Event()
        
    def create_feedback_mode(self, mode_name: str):
        """
        フィードバックモードを作成
        
        Args:
            mode_name: フィードバックモード名 ("increase", "decrease", "random")
            
        Returns:
            FeedbackMode: 選択されたフィードバックモード
            
        Raises:
            ValueError: 無効なモード名の場合
        """
        try:
            # 音声ファイルのパスを設定
            project_root = Path(__file__).parent.parent
            reward_sound = str(project_root / "assets" / "audio" / "high_sound.wav")
            punishment_sound = str(project_root / "assets" / "audio" / "low_sound.wav")
            
            # AudioFeedbackの初期化
            audio_feedback = AudioFeedback(reward_sound, punishment_sound)
            
            # モードに応じたフィードバッククラスを作成
            mode_map = {
                "increase": IncreaseRewardMode,
                "decrease": DecreaseRewardMode,
                "random": RandomMode
            }
            
            if mode_name not in mode_map:
                raise ValueError(f"Invalid feedback mode: {mode_name}")
            
            feedback_mode = mode_map[mode_name](audio_feedback)
            logger.info(f"Created feedback mode: {mode_name}")
            return feedback_mode
            
        except Exception as e:
            logger.error(f"Failed to create feedback mode: {e}")
            raise
    
    def setup_signal_handlers(self):
        """シグナルハンドラーの設定"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        # Ctrl+C (SIGINT) とTERM信号をハンドル
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Signal handlers configured")
    
    async def shutdown(self):
        """アプリケーションのシャットダウン"""
        logger.info("Shutting down application...")
        
        if self.session_controller and self.session_controller.is_running:
            logger.info("Stopping session...")
            await self.session_controller.stop_session()
        
        self.shutdown_event.set()
        logger.info("Application shutdown complete")
    
    def parse_arguments(self):
        """
        コマンドライン引数の解析
        
        Returns:
            argparse.Namespace: 解析された引数
        """
        parser = argparse.ArgumentParser(
            description='心拍バイオフィードバック実験プログラム',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用例:
  %(prog)s --mode increase     心拍数増加で報酬音を再生
  %(prog)s --mode decrease     心拍数減少で報酬音を再生
  %(prog)s --mode random       ランダムに報酬音を再生
  %(prog)s --mode increase --device POLAR_H10_12345678  特定デバイスを指定
            """
        )
        
        parser.add_argument(
            '--mode',
            choices=['increase', 'decrease', 'random'],
            required=True,
            help='フィードバックモード (increase/decrease/random)'
        )
        
        parser.add_argument(
            '--device',
            type=str,
            help='Polarデバイス ID（省略時は自動検出）'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='詳細ログを表示'
        )
        
        return parser.parse_args()
    
    async def run(self):
        """
        アプリケーションのメイン実行
        """
        try:
            # コマンドライン引数の解析
            args = self.parse_arguments()
            
            # ログレベルの設定
            if args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)
                logger.debug("Debug logging enabled")
            
            # シグナルハンドラーの設定
            self.setup_signal_handlers()
            
            # フィードバックモードの作成
            feedback_mode = self.create_feedback_mode(args.mode)
            
            # SessionControllerの初期化
            self.session_controller = SessionController(
                feedback_mode=feedback_mode,
                device_id=args.device
            )
            
            logger.info(f"Starting session with mode: {args.mode}")
            if args.device:
                logger.info(f"Target device: {args.device}")
            
            # セッション開始
            start_success = await self.session_controller.start_session()
            
            if not start_success:
                logger.error("Failed to start session")
                return 1
            
            logger.info("Session started - monitoring heart rate data")
            logger.info("Press Ctrl+C to stop")
            
            # シャットダウンまで待機
            await self.shutdown_event.wait()
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("User interrupted")
            await self.shutdown()
            return 0
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            await self.shutdown()
            return 1


async def main():
    """
    メイン関数
    
    Returns:
        int: 終了コード（0: 成功、1: エラー）
    """
    app = HeartRateBiofeedbackApp()
    return await app.run()


def main_sync():
    """
    同期版メイン関数（エントリーポイント用）
    
    Returns:
        int: 終了コード
    """
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main_sync()
    sys.exit(exit_code)
