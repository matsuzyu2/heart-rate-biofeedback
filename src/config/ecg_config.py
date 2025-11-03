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
BEAT_LOG_DIRECTORY = "logs/beat"
INSTANTANEOUS_HR_LOG_DIRECTORY = "logs/instantaneous_hr"

# 心拍数解析設定
HR_TREND_THRESHOLD_BPM = 1.0  # トレンド判定の閾値（BPM）
HR_BLOCK_WINDOW_SECONDS = 5.0  # ブロック平均の時間窓（秒）
HR_FILTER_THRESHOLD_BPM = 5.0  # 瞬間心拍数フィルタリングの閾値（BPM）

# 過渡応答除外設定
TRANSITION_PERIOD_SECONDS = 5.0  # Polarセンサー装着時の過渡応答期間（秒）

# セッション自動終了設定
SESSION_DURATION_SECONDS = 900  # 実験時間（秒）
