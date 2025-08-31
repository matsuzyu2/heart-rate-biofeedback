"""
sensorモジュールのテストコード
Polar H9/H10対応インターフェースのテスト（設定ファイル対応）
"""
import unittest
from unittest.mock import patch, AsyncMock
import asyncio

# テスト対象のインポート（相対インポート）
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.sensor.polar_interface import PolarInterface, scan_for_polar_devices
from src.config.sensor_config import POLAR_DEVICE_ID


class TestPolarInitialization(unittest.TestCase):
    """
    Polar心拍センサーの初期化テスト
    単一責任原則（SRP）: 初期化のみを責務とする
    """
    
    def test_初期化_デバイスID指定あり(self):
        """デバイスIDを指定した初期化をテスト"""
        device_id = "EBC5752E"
        polar = PolarInterface(device_id=device_id)
        
        # 基本的な属性が存在することを確認
        self.assertEqual(polar.device_id, device_id)
        self.assertFalse(polar.is_connected)
        self.assertIsNone(polar.client)
        self.assertIsNone(polar.device_address)
        self.assertIsNone(polar.device_name)
    
    def test_初期化_デバイスID指定なし(self):
        """デバイスIDを指定しない初期化をテスト（設定ファイルから読み込み）"""
        polar = PolarInterface()
        
        # 設定ファイルからデバイスIDが読み込まれることを確認
        self.assertEqual(polar.device_id, POLAR_DEVICE_ID)
        self.assertFalse(polar.is_connected)
        self.assertIsNone(polar.client)
        self.assertIsNone(polar.device_address)  # 初期状態ではNone（自動検出前）
    
    def test_設定ファイル読み込み(self):
        """設定ファイルからの設定読み込みをテスト"""
        # デバイスIDが設定ファイルから正しく読み込まれることを確認
        self.assertEqual(POLAR_DEVICE_ID, "EBC5752E")
        
        # 引数なしでの初期化で設定ファイルの値が使用されることを確認
        polar = PolarInterface()
        self.assertEqual(polar.device_id, POLAR_DEVICE_ID)
        
        # 引数ありでの初期化で引数が優先されることを確認
        custom_id = "TEST123"
        polar_custom = PolarInterface(device_id=custom_id)
        self.assertEqual(polar_custom.device_id, custom_id)


class TestPolarDataProcessing(unittest.TestCase):
    """
    Polar心拍センサーのデータ処理テスト
    単一責任原則（SRP）: データ処理のみを責務とする
    """
    
    def setUp(self):
        """各テストの前に実行される初期化"""
        self.polar = PolarInterface()
    
    def test_心拍データ作成(self):
        """心拍数データの作成をテスト"""
        test_hr = 75
        
        # このテストは最初は失敗する（Red）- メソッド未実装のため
        data = self.polar.create_heart_rate_data(test_hr)
        
        # 期待されるデータ形式
        self.assertIn("heart_rate", data)
        self.assertIn("timestamp", data)
        self.assertEqual(data["heart_rate"], test_hr)


class TestPolarConnection(unittest.IsolatedAsyncioTestCase):
    """
    Polar心拍センサーの接続管理テスト
    単一責任原則（SRP）: 接続・切断のみを責務とする
    """
    
    async def asyncSetUp(self):
        """非同期テストの初期化"""
        self.polar = PolarInterface()
    
    @patch('src.sensor.polar_interface.BleakClient')
    @patch('src.sensor.polar_interface.PolarInterface.find_polar_device')
    async def test_接続(self, mock_find_device, mock_bleak_client):
        """基本的な接続をテスト"""
        # デバイス検出のモック設定
        mock_find_device.return_value = "AA:BB:CC:DD:EE:FF"
        
        # BLEクライアントのモック設定
        mock_client = AsyncMock()
        mock_bleak_client.return_value = mock_client
        mock_client.connect.return_value = True
        
        # 接続実行
        result = await self.polar.connect()
        
        # 検証
        self.assertTrue(result)
        self.assertTrue(self.polar.is_connected)
        self.assertEqual(self.polar.device_address, "AA:BB:CC:DD:EE:FF")
    
    async def test_切断(self):
        """基本的な切断をテスト"""
        # 接続状態をシミュレート
        mock_client = AsyncMock()
        self.polar.client = mock_client
        self.polar.is_connected = True
        
        # 切断実行
        await self.polar.disconnect()
        
        # 検証
        self.assertFalse(self.polar.is_connected)


class TestPolarRealDevice(unittest.IsolatedAsyncioTestCase):
    """
    Polar実機テスト（H9/H10対応）
    注意: 実際のPolarデバイスが必要です
    
    実行方法:
    - 全テスト実行: pytest tests/test_sensor.py
    - 実機テストのみ: pytest tests/test_sensor.py::TestPolarRealDevice
    - 実機テスト除外: pytest tests/test_sensor.py -k "not RealDevice"
    """
    
    def setUp(self):
        """実機テストの前に環境チェック"""
        # 環境変数で実機テストを制御
        skip_real_device = os.getenv('SKIP_REAL_DEVICE_TESTS', 'false').lower() == 'true'
        if skip_real_device:
            self.skipTest("実機テストはSKIP_REAL_DEVICE_TESTS=trueによりスキップされました")
    
    async def asyncSetUp(self):
        """非同期テストの初期化（設定ファイル使用）"""
        # 設定ファイルからデバイスIDを使用（引数なしで初期化）
        self.polar = PolarInterface()  # 設定ファイルからEBC5752Eが読み込まれる
        self.received_data = []
    
    def heart_rate_callback(self, data):
        """テスト用のコールバック関数"""
        self.received_data.append(data)
        print(f"📊 心拍数データ受信: {data['heart_rate']} BPM")
    
    async def test_デバイススキャン(self):
        """実機: Polarデバイス（H9/H10）のスキャンテスト"""
        print("\n🔍 Polarデバイスをスキャン中...")
        
        try:
            devices = await scan_for_polar_devices()
            
            # デバイスが見つからない場合はスキップ（エラーではない）
            if not devices:
                self.skipTest("Polarデバイスが見つかりませんでした。電源とBluetoothを確認してください。")
            
            print(f"✅ {len(devices)}個のPolarデバイスが見つかりました")
            for device in devices:
                print(f"  - {device.name} ({device.address})")
            
            # 最低1個のデバイスが見つかることを確認
            self.assertGreater(len(devices), 0)
            
        except Exception as e:
            self.fail(f"デバイススキャンでエラーが発生: {e}")
    
    async def test_実機接続(self):
        """実機: 基本的な接続・切断テスト"""
        print("\n🔗 実機接続テスト開始...")
        
        try:
            # 接続テスト
            print(f"接続試行中: {self.polar.device_address}")
            connected = await self.polar.connect()
            
            if not connected:
                self.skipTest(f"Polarデバイス({self.polar.device_address})に接続できませんでした。デバイスアドレスとデバイス状態を確認してください。")
            
            print("✅ 接続成功!")
            self.assertTrue(self.polar.is_connected)
            
            # 少し待機
            await asyncio.sleep(1)
            
            # 切断テスト
            await self.polar.disconnect()
            print("✅ 切断成功!")
            self.assertFalse(self.polar.is_connected)
            
        except Exception as e:
            # クリーンアップ
            if self.polar.is_connected:
                await self.polar.disconnect()
            self.fail(f"実機接続テストでエラーが発生: {e}")
    
    async def test_実機データ受信(self):
        """実機: 心拍数データ受信テスト"""
        print("\n📊 実機データ受信テスト開始...")
        
        # コールバック設定
        self.polar.set_heart_rate_callback(self.heart_rate_callback)
        
        try:
            # 接続
            print("接続中...")
            connected = await self.polar.connect()
            
            if not connected:
                self.skipTest("実機に接続できませんでした。データ受信テストをスキップします。")
            
            print("✅ 接続成功")
            
            # モニタリング開始
            print("心拍数モニタリング開始...")
            monitoring_started = await self.polar.start_heart_rate_monitoring()
            
            if not monitoring_started:
                await self.polar.disconnect()
                self.fail("心拍数モニタリングの開始に失敗しました")
            
            print("✅ モニタリング開始成功")
            print("⏰ 5秒間データを受信します...")
            
            # 5秒間データ受信
            await asyncio.sleep(5)
            
            # モニタリング停止
            await self.polar.stop_heart_rate_monitoring()
            await self.polar.disconnect()
            
            # 結果検証
            print(f"📈 受信データ数: {len(self.received_data)}")
            
            if self.received_data:
                print("✅ データ受信成功!")
                print(f"最新データ: {self.received_data[-1]}")
                
                # データ形式の検証
                latest_data = self.received_data[-1]
                self.assertIn("heart_rate", latest_data)
                self.assertIn("timestamp", latest_data)
                self.assertIsInstance(latest_data["heart_rate"], int)
                self.assertGreater(latest_data["heart_rate"], 0)
            else:
                print("⚠️ データを受信できませんでした")
                print("確認事項:")
                print("  - Polarデバイスを胸に正しく装着しているか")
                print("  - ストラップが濡れているか（導電性向上のため）")
                print("  - デバイスが正常に動作しているか")
                self.skipTest("心拍数データを受信できませんでした。装着状態を確認してください。")
                
        except Exception as e:
            # クリーンアップ
            if self.polar.is_connected:
                await self.polar.stop_heart_rate_monitoring()
                await self.polar.disconnect()
            self.fail(f"実機データ受信テストでエラーが発生: {e}")


if __name__ == '__main__':
    # テスト実行時の使用例を表示
    print("🧪 Polarセンサーテスト（H9/H10対応）")
    print("=" * 50)
    print("モックテストのみ実行:")
    print("  pytest tests/test_sensor.py -k 'not RealDevice'")
    print()
    print("実機テストのみ実行:")
    print("  pytest tests/test_sensor.py::TestPolarRealDevice")
    print()
    print("全テスト実行:")
    print("  pytest tests/test_sensor.py")
    print("=" * 50)
    
    unittest.main(verbosity=2)