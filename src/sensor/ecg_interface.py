# ECG専用Polarインターフェース
import asyncio
from bleak import BleakClient, BleakScanner
import logging

# ECG専用設定を読み込み
from ..config.ecg_config import (
    ECG_POLAR_DEVICE_ID,
    ECG_SERVICE_UUID,
    ECG_CONTROL_POINT_UUID,
    ECG_DATA_UUID,
    ECG_TIMEOUT_SECONDS,
    TRANSITION_PERIOD_SECONDS
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ECGDataFormatter:
    """
    ECG生データの変換専用クラス
    """
    
    def __init__(self):
        """ECGDataFormatterを初期化"""
        pass
    
    def convert_array_to_signed_int(self, data, offset, length):
        """バイト配列を符号付き整数に変換"""
        return int.from_bytes(
            bytearray(data[offset : offset + length]), byteorder="little", signed=True,
        )

    def convert_to_unsigned_long(self, data, offset, length):
        """バイト配列を符号なし長整数に変換"""
        return int.from_bytes(
            bytearray(data[offset : offset + length]), byteorder="little", signed=False,
        )  
    
    def parse_ecg_data(self, raw_data):
        """
        Polarセンサーからの生ECGデータを解析
        
        Args:
            raw_data (bytes): Polarセンサーからの生ECGデータ
            
        Returns:
            dict: ECGサンプルデータと処理情報を含む辞書
                {
                    'ecg_samples': list,  # ECGサンプル値のリスト
                    'timestamps': list,   # 各サンプルのタイムスタンプ（絶対時刻ナノ秒数）
                }
        """
        # 最小ヘッダーサイズ確認
        if len(raw_data) < 10:
            raise ValueError(f"Insufficient ECG data length: {len(raw_data)} bytes")

        # データタイプがECGかチェック
        if raw_data[0] != 0x00:
            raise ValueError(f"Received unknown data type: {raw_data[0]}")
        
        try:
            # タイムスタンプを抽出
            timestamp = self.convert_to_unsigned_long(raw_data, 1, 8)
            
            # フレームタイプを抽出
            frame_type = raw_data[9]
            
            # ECGサンプルデータを抽出
            ecg_payload_bytes = raw_data[10:]

            ecg_samples = []
            timestamps = []

            # 3バイト/サンプル処理（24bit signed integer）
            if frame_type == 0x00:
                bytes_per_ecg_sample = 3
                ecg_samples_count = len(ecg_payload_bytes) // bytes_per_ecg_sample
                
                for i in range(ecg_samples_count):
                    byte_offset = i * bytes_per_ecg_sample
                    current_sample_bytes = ecg_payload_bytes[byte_offset:byte_offset + bytes_per_ecg_sample]
                    
                    # 24ビット符号付き整数に変換
                    ecg_value = self.convert_array_to_signed_int(current_sample_bytes, 0, bytes_per_ecg_sample)
                    
                    # サンプル時刻計算（130Hzでの各サンプル時刻）
                    current_sample_timestamp_ns = timestamp + (i * 1_000_000_000 // 130)
                    
                    ecg_samples.append(ecg_value)
                    timestamps.append(current_sample_timestamp_ns)
                
                return {
                    'ecg_samples': ecg_samples,
                    'timestamps': timestamps,
                }
            else:
                raise ValueError(f"Unsupported frame type: {frame_type}")
                
        except Exception as e:
            raise ValueError(f"Failed to parse ECG data: {e}")


class ECGInterface:
    """
    Polar ECG専用インターフェースクラス
    """
    
    def __init__(self):
        """
        Polar ECGインターフェースを初期化
        
        デバイスIDは ecg_config.ECG_POLAR_DEVICE_ID から取得
        """
        self.device_id = ECG_POLAR_DEVICE_ID
        self.device_address = None
        self.device_name = None
        self.client = None
        self.is_connected = False
        self.is_streaming = False
        self.ecg_callback = None

        # 過渡応答除外関連
        self.streaming_start_time_ns = None
        self.transition_period_seconds = TRANSITION_PERIOD_SECONDS
        self.transition_period_passed = False  # 過渡応答期間が終了したかのフラグ

        self.data_formatter = ECGDataFormatter()

    def set_ecg_callback(self, callback):
        """
        ECGデータ受信時のコールバック関数を設定
        
        Args:
            callback (callable): ECGデータを受信した際に呼び出される関数
        """
        self.ecg_callback = callback
    
    async def find_polar_device(self):
        """Polarデバイスを検出"""
        logger.info(f"Searching for Polar device with ID: {self.device_id}")
        devices = await BleakScanner.discover(timeout=ECG_TIMEOUT_SECONDS)
        
        for device in devices:
            if device.name and "Polar" in device.name and self.device_id in device.name:
                logger.info(f"Found target Polar device: {device.name} ({device.address})")
                self.device_name = device.name
                return device.address
        
        return None
    
    def _filter_transition_data(self, ecg_result):
        """
        過渡応答期間のデータをフィルタリング
        
        Args:
            ecg_result (dict): ECGデータ結果
            
        Returns:
            dict or None: フィルタリング後のECGデータ、過渡応答期間中の場合はNone
        """
        # 過渡応答期間が既に終了している場合はフィルタリングしない
        if self.transition_period_passed:
            return ecg_result
        
        # 最初のデータ受信時にストリーミング開始時刻を設定
        if self.streaming_start_time_ns is None:
            timestamps = ecg_result.get('timestamps', [])
            if timestamps:
                self.streaming_start_time_ns = timestamps[0]
                logger.info("Set streaming start time for transition filtering")
        
        if self.streaming_start_time_ns is None:
            # タイムスタンプが取得できない場合はデータを破棄
            return None
        
        # パケット内のタイムスタンプをチェック
        timestamps = ecg_result.get('timestamps', [])
        ecg_samples = ecg_result.get('ecg_samples', [])
        
        if not timestamps or not ecg_samples:
            return None
        
        # 過渡応答期間を超えたサンプルのインデックスを見つける
        valid_indices = []
        for i, timestamp_ns in enumerate(timestamps):
            elapsed_seconds = (timestamp_ns - self.streaming_start_time_ns) / 1_000_000_000
            if elapsed_seconds >= self.transition_period_seconds:
                valid_indices.append(i)
        
        # 有効なサンプルがない場合
        if not valid_indices:
            return None
        
        # 有効なサンプルがある場合
        if valid_indices:
            # 部分的にフィルタリング
            filtered_samples = [ecg_samples[i] for i in valid_indices]
            filtered_timestamps = [timestamps[i] for i in valid_indices]
            
            self.transition_period_passed = True  # 過渡応答期間終了
            logger.info("Transition period completed - no more filtering needed")
            
            return {
                'ecg_samples': filtered_samples,
                'timestamps': filtered_timestamps
            }
    
    async def ecg_notification_handler(self, sender, data):
        """ECGデータの通知を処理（polar_h10_get_ecg.py仕様準拠）"""
        try:
            # ECGデータ解析（PMD仕様準拠）
            ecg_result = self.data_formatter.parse_ecg_data(data)
            
            # 過渡応答期間のデータをフィルタリング
            filtered_result = self._filter_transition_data(ecg_result)
            if filtered_result is None:
                return
            
            # データをリストに蓄積
            ecg_samples = filtered_result['ecg_samples']
            timestamps = filtered_result['timestamps']
            
            ecg_samples_count = len(ecg_samples)
            logger.info(f"Processed {ecg_samples_count} ECG samples from packet (frame_type=0)")
            
            if self.ecg_callback:
                self.ecg_callback(filtered_result)
                
        except Exception as e:
            logger.error(f"Error processing ECG data: {e}")
    
    async def connect(self):
        """Polarセンサーに接続"""
        try:
            self.device_address = await self.find_polar_device()
            
            if self.device_address is None:
                logger.error(f"Polar device with ID '{self.device_id}' not found")
                return False
            
            logger.info(f"Connecting to ECG device: {self.device_address}")
            self.client = BleakClient(self.device_address)
            await self.client.connect()
            self.is_connected = True
            logger.info("Successfully connected to ECG service")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ECG service: {e}")
            return False
    
    async def disconnect(self):
        """接続を切断"""
        if self.is_streaming:
            await self.stop_ecg_streaming()
            
        if self.client and self.is_connected:
            try:
                await self.client.disconnect()
                self.is_connected = False
                logger.info("Successfully disconnected from ECG service")
            except Exception as e:
                logger.error(f"Failed to disconnect from ECG service: {e}")
    
    async def start_ecg_streaming(self):
        """ECGストリーミングを開始"""
        if not self.is_connected:
            logger.error("Not connected to ECG device")
            return False
            
        try:
            # ECG測定の通知を開始
            await self.client.start_notify(ECG_DATA_UUID, self.ecg_notification_handler)
            
            # ECGストリーミング開始コマンドを送信
            start_command = bytearray([0x02, 0x00, 0x00, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00])
            await self.client.write_gatt_char(ECG_CONTROL_POINT_UUID, start_command)
            
            # ストリーミング開始時刻は最初のデータ受信時に設定
            self.streaming_start_time_ns = None
            self.transition_period_passed = False  # フラグをリセット
            
            self.is_streaming = True
            logger.info("ECG streaming started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start ECG streaming: {e}")
            return False
    
    async def stop_ecg_streaming(self):
        """ECGストリーミングを停止"""
        if self.client and self.is_connected and self.is_streaming:
            try:
                # ECGストリーミング停止コマンドを送信（PMDプロトコル準拠）
                stop_command = bytearray([0x03, 0x00])  # ECGストリーミング停止
                await self.client.write_gatt_char(ECG_CONTROL_POINT_UUID, stop_command)
                
                # 通知を停止
                await self.client.stop_notify(ECG_DATA_UUID)
                
                self.is_streaming = False
                logger.info("ECG streaming stopped")
                
            except Exception as e:
                logger.error(f"Failed to stop ECG streaming: {e}")


async def main():
    """ECGインターフェースのテスト用メイン処理"""
    ecg_interface = ECGInterface()
    
    try:
        # 接続
        if await ecg_interface.connect():
            # ECGストリーミング開始
            if await ecg_interface.start_ecg_streaming():
                logger.info("Monitoring ECG data... Press Ctrl+C to stop")
                
                try:
                    # 30秒間ECGデータを監視
                    await asyncio.sleep(30)
                except KeyboardInterrupt:
                    logger.info("Stopping ECG monitoring...")
        
        # クリーンアップ
        await ecg_interface.stop_ecg_streaming()
        await ecg_interface.disconnect()
        
    except Exception as e:
        logger.error(f"Error in ECG main: {e}")
        if ecg_interface.is_connected:
            await ecg_interface.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
