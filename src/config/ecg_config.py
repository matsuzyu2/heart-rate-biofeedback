# ECG専用設定ファイル

# Polarデバイス設定
ECG_POLAR_DEVICE_ID = "D9DB7D2A"

# ECG Service UUID（Polar独自）
ECG_SERVICE_UUID = "fb005c80-02e7-f387-1cad-8acd2d8df0c8"
ECG_CONTROL_POINT_UUID = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"  # PMD Control（コマンド送信用）
ECG_DATA_UUID = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"  # PMD Data（データ受信用）

# ECGデータ取得設定
ECG_SAMPLING_RATE = 130
ECG_TIMEOUT_SECONDS = 30

# データ記録設定
ECG_LOG_DIRECTORY = "logs/ecg"
