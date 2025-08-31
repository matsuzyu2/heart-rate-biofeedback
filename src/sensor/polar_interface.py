# Polar心拍センサー（H9/H10対応）との通信インターフェース
import asyncio
from bleak import BleakClient, BleakScanner
from datetime import datetime
import logging

# 設定ファイルから設定を読み込み（相対インポート）
from ..config.sensor_config import POLAR_DEVICE_ID

# Heart Rate Serviceの特性UUID（Bluetooth SIG標準）
HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# データ解析用定数
HEART_RATE_FLAGS_INDEX = 0
HEART_RATE_VALUE_INDEX = 1
MIN_DATA_LENGTH = 2

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeartRateDataProcessor:
    """
    心拍数データの処理専用クラス
    単一責任原則（SRP）: データ変換・処理のみを責務とする
    """
    
    def create_heart_rate_data(self, heart_rate):
        """
        心拍数データを標準形式で作成
        
        Args:
            heart_rate (int): 心拍数（BPM）
            
        Returns:
            dict: 標準化された心拍数データ
        """
        return {
            "heart_rate": heart_rate,
            "timestamp": datetime.now().isoformat()
        }
    
    def parse_raw_data(self, raw_data):
        """
        Polarセンサーからの生データを解析（H9/H10対応）
        
        Args:
            raw_data (bytes): Polarセンサーからの生データ
            
        Returns:
            int: 心拍数（BPM）
            
        Raises:
            ValueError: データが不正な場合
        """
        if len(raw_data) < MIN_DATA_LENGTH:
            raise ValueError(f"Insufficient data length: {len(raw_data)}")
        
        return raw_data[HEART_RATE_VALUE_INDEX]


class PolarInterface:
    """
    Polar心拍センサーインターフェースクラス（H9/H10対応）
    責任分離: データ処理は別クラスに委譲、接続管理は自身で処理
    """
    
    def __init__(self, device_id=None):
        """
        Polar心拍センサーインターフェースを初期化
        
        Args:
            device_id (str, optional): PolarセンサーのデジタルID（デバイス名に含まれる）
                                     優先順位: 引数 > 環境変数 > 設定ファイル
                                     Noneの場合は設定ファイルの値を使用
        """
        # 設定の優先順位: 引数 > 環境変数 > 設定ファイル（YAGNI: 環境変数は将来必要なら追加）
        self.device_id = device_id or POLAR_DEVICE_ID
        self.device_address = None  # 自動検出で設定される
        self.device_name = None  # 検出されたデバイス名
        self.client = None
        self.is_connected = False
        self.heart_rate_callback = None
        
        # データ処理を専用クラスに委譲（責任分離）
        self.data_processor = HeartRateDataProcessor()
    
    async def find_polar_device(self):
        """Polarデバイス（H9/H10）を検出"""
        devices = await BleakScanner.discover()
        
        for device in devices:
            if device.name and "Polar" in device.name:
                # 特定のデバイスIDが指定されている場合
                if self.device_id and self.device_id in device.name:
                    logger.info(f"Found target Polar device: {device.name} ({device.address})")
                    self.device_name = device.name
                    return device.address
                # デバイスIDが指定されていない場合は最初のPolarデバイスを使用
                elif self.device_id is None:
                    logger.info(f"Found Polar device: {device.name} ({device.address})")
                    self.device_name = device.name
                    return device.address
        
        return None
    
    def create_heart_rate_data(self, heart_rate):
        """心拍数データを作成（データ処理クラスに委譲）"""
        return self.data_processor.create_heart_rate_data(heart_rate)
    
    def set_heart_rate_callback(self, callback):
        """心拍数データを受信した際のコールバック関数を設定"""
        self.heart_rate_callback = callback
    
    async def notification_handler(self, sender, data):
        """心拍数データの通知を処理"""
        try:
            # データ解析（データ処理クラスに委譲）
            heart_rate = self.data_processor.parse_raw_data(data)
            
            # 標準形式で作成（データ処理クラスに委譲）
            heart_rate_data = self.data_processor.create_heart_rate_data(heart_rate)
            
            # ログ出力
            logger.info(f"Heart Rate: {heart_rate} BPM (from {self.device_name})")
            
            # コールバック実行
            if self.heart_rate_callback:
                self.heart_rate_callback(heart_rate_data)
                
        except Exception as e:
            logger.error(f"Error processing heart rate data: {e}")
    
    async def connect(self):
        """Polarセンサーに接続"""
        try:
            # Polarデバイスを自動検出
            if self.device_id:
                logger.info(f"Searching for Polar device with ID: {self.device_id}")
            else:
                logger.info("Searching for any Polar device...")
            
            self.device_address = await self.find_polar_device()
            
            if self.device_address is None:
                if self.device_id:
                    logger.error(f"Polar device with ID '{self.device_id}' not found")
                else:
                    logger.error("No Polar devices found")
                return False
            
            logger.info(f"Connecting to device: {self.device_address}")
            self.client = BleakClient(self.device_address)
            await self.client.connect()
            self.is_connected = True
            logger.info("Successfully connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """接続を切断"""
        if self.client and self.is_connected:
            try:
                await self.client.disconnect()
                self.is_connected = False
                logger.info("Successfully disconnected")
            except Exception as e:
                logger.error(f"Failed to disconnect: {e}")
    
    async def start_heart_rate_monitoring(self):
        """心拍数モニタリングを開始"""
        if not self.is_connected:
            logger.error("Not connected to device")
            return False
            
        try:
            await self.client.start_notify(HEART_RATE_MEASUREMENT_UUID, self.notification_handler)
            logger.info("Heart rate monitoring started")
            return True
        except Exception as e:
            logger.error(f"Failed to start heart rate monitoring: {e}")
            return False
    
    async def stop_heart_rate_monitoring(self):
        """心拍数モニタリングを停止"""
        if self.client and self.is_connected:
            try:
                await self.client.stop_notify(HEART_RATE_MEASUREMENT_UUID)
                logger.info("Heart rate monitoring stopped")
            except Exception as e:
                logger.error(f"Failed to stop heart rate monitoring: {e}")


async def scan_for_polar_devices(device_id=None):
    """Polarデバイス（H9/H10）をスキャン"""
    logger.info("Scanning for Polar devices...")
    devices = await BleakScanner.discover()
    polar_devices = []
    
    for device in devices:
        if device.name and "Polar" in device.name:
            # 特定のデバイスIDが指定されている場合はフィルタリング
            if device_id is None or device_id in device.name:
                polar_devices.append(device)
                logger.info(f"Found Polar device: {device.name} ({device.address})")
    
    return polar_devices


async def main():
    """メイン処理"""
    # デバイスIDを指定しない場合は最初に見つかったPolarデバイスを使用
    polar_interface = PolarInterface()
    
    try:
        # 接続
        if await polar_interface.connect():
            # 心拍数モニタリング開始
            if await polar_interface.start_heart_rate_monitoring():
                logger.info("Monitoring heart rate... Press Ctrl+C to stop")
                
                # 無限ループで心拍数を監視
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Stopping heart rate monitoring...")
                    
        # クリーンアップ
        await polar_interface.stop_heart_rate_monitoring()
        await polar_interface.disconnect()
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        if polar_interface.is_connected:
            await polar_interface.disconnect()


def run_heart_rate_monitor():
    """同期的なエントリーポイント（既存コードとの互換性のため）"""
    asyncio.run(main())


if __name__ == "__main__":
    # 非同期でメイン処理を実行
    asyncio.run(main())
