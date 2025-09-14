import asyncio
from bleak import BleakScanner, BleakClient
import pandas as pd

# 1. 接続先のデバイス名をサーバーのものに合わせる
POLAR_H10_NAME = "Polar H10 D9DB7D2A"  # 実際のデバイス名に変更

# ECGデータストリームのUUID
PMD_SERVICE = "FB005C80-02E7-F387-1CAD-8ACD2D8DF0C8"
PMD_CONTROL = "FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8"
PMD_DATA = "FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8"
ECG_WRITE = bytearray([0x02, 0x00, 0x00, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00])

ecg_session_data = []  # ECGセッションのデータを保存するリスト
ecg_session_time = []  # ECGセッションのタイムスタンプを保存するリスト

# 2. データ受信関数を実際のPolar H10仕様に修正
def process_ecg_notification(sender, raw_ecg_data: bytearray):
    """
    受信したデータを処理するコールバック関数（Polar H10 PMD仕様）
    実際のPolar H10は [1-byte type][8-byte timestamp][1-byte frame_type][ECG samples...] の形式で送信する。
    """
    # 最小ヘッダーサイズ確認
    if len(raw_ecg_data) < 10:
        print(f"Error: Data too short: {len(raw_ecg_data)} bytes")
        return

    # データタイプがECG(0x00)かチェック
    if raw_ecg_data[0] == 0x00:
        # タイムスタンプを抽出 (Bytes 1-8)
        timestamp = convert_to_unsigned_long(raw_ecg_data, 1, 8)
        
        # フレームタイプ (Byte 9)
        frame_type = raw_ecg_data[9]
        
        # ECGサンプルデータ (Byte 10以降)
        ecg_payload_bytes = raw_ecg_data[10:]

        # Type 0: 3バイト/サンプル処理
        if frame_type == 0x00:
            bytes_per_ecg_sample = 3
            ecg_samples_count = len(ecg_payload_bytes) // bytes_per_ecg_sample
            
            for i in range(ecg_samples_count):
                byte_offset = i * bytes_per_ecg_sample
                current_sample_bytes = ecg_payload_bytes[byte_offset:byte_offset + bytes_per_ecg_sample]
                
                # 24ビット符号付き整数に変換
                ecg_value = convert_array_to_signed_int(current_sample_bytes, 0, bytes_per_ecg_sample)
                
                # サンプル時刻計算（130Hzでの各サンプル時刻）
                current_sample_timestamp_ns = timestamp + (i * 1_000_000_000 // 130)
                
                # データをリストに追加
                ecg_session_data.append(ecg_value)
                ecg_session_time.append(current_sample_timestamp_ns)
            
            print(f"Processed {ecg_samples_count} ECG samples from packet (frame_type={frame_type})")
        else:
            print(f"Unsupported frame type: {frame_type}")
    else:
        print(f"Received unknown data type: {raw_ecg_data[0]}")


def convert_array_to_signed_int(data, offset, length):
    """バイト配列を符号付き整数に変換"""
    return int.from_bytes(
        bytearray(data[offset : offset + length]), byteorder="little", signed=True,
    )


def convert_to_unsigned_long(data, offset, length):
    """バイト配列を符号なし長整数に変換"""
    return int.from_bytes(
        bytearray(data[offset : offset + length]), byteorder="little", signed=False,
    )


async def run():
    """メインの非同期処理"""
    print(f"Scanning for '{POLAR_H10_NAME}'...")
    device = await BleakScanner.find_device_by_name(POLAR_H10_NAME, timeout=20.0)

    if not device:
        print(f"Device '{POLAR_H10_NAME}' not found!")
        return
    
    print(f"Found device: {device.name} ({device.address})")

    async with BleakClient(device) as client:
        print(f"Connecting to {device.address}...")
        await client.connect(timeout=20.0)
        print("Connected.")

        print("Sending ECG start command...")
        await client.write_gatt_char(PMD_CONTROL, ECG_WRITE)
        
        print("Starting notifications...")
        await client.start_notify(PMD_DATA, process_ecg_notification)
        
        # 実際のPolar H10からECGデータを収集
        # (ここでは15秒に設定)
        print("Collecting data for 15 seconds...")
        await asyncio.sleep(15.0)
        
        print("Stopping notifications...")
        await client.stop_notify(PMD_DATA)
        print("Disconnected.")

        if not ecg_session_data:
            print("No data was collected. Exiting.")
            return

        df = pd.DataFrame({
            "timestamp": ecg_session_time,
            "ecg": ecg_session_data
        })
        
        df = df.sort_values(by="timestamp").reset_index(drop=True)
        
        if not df.empty:
            start_time = df['timestamp'].iloc[0]
            df['timestamp'] = (df['timestamp'] - start_time) / 1_000_000_000
        
        df.to_csv("ecg_data_from_server.csv", index=False)
        print("ECGデータをecg_data_from_server.csvに保存しました")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Program stopped by user.")