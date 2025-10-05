# Heart Rate Biofeedback System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

リアルタイムECG心拍数監視による音声バイオフィードバック実験システムです。Polar H9/H10心拍センサーを使用して、心拍数の意識的なコントロール能力を測定・訓練します。

## 🎯 概要

このシステムはECG心拍数バイオフィードバック実験のために設計されました。被験者は3つの異なるモードで心拍数をコントロールし、その能力を測定・向上させることができます。

### 主な特徴

- 🫀 **リアルタイムECG心拍数監視**: Polar H9/H10センサーによる高精度ECG測定（130Hz）
- 🔊 **即座の音声フィードバック**: R波検出に基づく瞬間心拍数による低遅延応答
- 📊 **3つの実験モード**: 増加報酬・減少報酬・ランダム制御
- 📈 **3種類のデータ記録**: ECG生データ、R波検出イベント、瞬間心拍数トレンド
- 🛡️ **過渡応答除外機能**: センサー装着直後5秒間のデータを自動除外

## 🚀 クイックスタート

### 必要要件

- Python 3.11以上
- Polar H9またはH10心拍センサー
- Bluetooth対応デバイス
- macOS / Linux / Windows

### インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/matsuzyu2/heart-rate-biofeedback.git
cd heart-rate-biofeedback
```

2. 仮想環境を作成・有効化:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# または
.venv\Scripts\activate  # Windows
```

3. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

### 使用方法

1. **心拍センサーの準備**:
   - Polar H9/H10を胸部に装着
   - センサーがアクティブになるまで待機

2. **実験の実行**:
```bash
# 心拍数増加報酬モード
python src/ecg_main.py --mode increase

# 心拍数減少報酬モード  
python src/ecg_main.py --mode decrease

# ランダム制御モード（対照群）
python src/ecg_main.py --mode random
```

3. **実験終了**:
   - `Ctrl+C`で安全に終了
   - セッションデータは自動保存

## 📋 実験モード

### 1. 増加報酬モード (`--mode increase`)
- 心拍数が増加トレンド（+1.0 BPM以上）を示すと報酬音が再生
- 心拍数が減少トレンドを示すと罰音が再生
- 心拍数上昇の意識的コントロールを訓練

### 2. 減少報酬モード (`--mode decrease`)  
- 心拍数が減少トレンド（-1.0 BPM以下）を示すと報酬音が再生
- 心拍数が増加トレンドを示すと罰音が再生
- リラクゼーション・瞑想効果を測定

### 3. ランダム制御モード (`--mode random`)
- ランダムなタイミングで報酬音または罰音を再生
- 制御群としての比較データ取得

## 💾 データ記録

実験中、以下の3種類のログファイルが自動生成されます：

### 1. ECG生データ (`logs/ecg/`)
- **ファイル名**: `ecg_YYYYMMDD_HHMMSS.csv`
- **内容**: ECGサンプル値とタイムスタンプ
- **サンプリングレート**: 130Hz
- **フォーマット**: `record_id,timestamp_ns,sample_value`

### 2. R波検出イベント (`logs/beat/`)
- **ファイル名**: `beat_YYYYMMDD_HHMMSS.csv`
- **内容**: R波検出時のタイムスタンプ、振幅、RR間隔
- **フォーマット**: `timestamp_ns,sample_index,amplitude,rr_interval_ms`

### 3. 瞬間心拍数トレンド (`logs/instantaneous_hr/`)
- **ファイル名**: `instantaneous_hr_YYYYMMDD_HHMMSS.csv`
- **内容**: 瞬間心拍数とRR間隔（5秒ごとの平均値とトレンド判定に使用）
- **フォーマット**: `timestamp_ns,rr_interval_ms,instantaneous_hr_bpm`

## 🔧 設定

### ECGセンサー設定

設定ファイル: `src/config/ecg_config.py`

```python
# Polarデバイス設定
ECG_POLAR_DEVICE_ID = "D9DB7D2A"

# ECGデータ取得設定
ECG_SAMPLING_RATE = 130  # Hz
ECG_TIMEOUT_SECONDS = 30

# 心拍数解析設定
HR_TREND_THRESHOLD_BPM = 1.0  # トレンド判定の閾値（BPM）
HR_BLOCK_WINDOW_SECONDS = 5.0  # ブロック平均の時間窓（秒）

# 過渡応答除外設定
TRANSITION_PERIOD_SECONDS = 5.0  # センサー装着時の過渡応答期間（秒）
```

### 音声ファイル

- **報酬音**: `assets/audio/high_sound.wav`
- **罰音**: `assets/audio/low_sound.wav`

必要に応じて独自の音声ファイルに置き換え可能です。

## 🔬 技術的詳細

### ECG処理パイプライン

1. **ECGデータ取得**: Polar H9/H10から130HzでECGサンプルを取得
2. **R波検出**: シンプルな閾値ベースのR波検出アルゴリズム
3. **RR間隔計算**: 連続するR波間の時間間隔を計算
4. **瞬間心拍数算出**: RR間隔から瞬間心拍数（BPM）を計算
5. **トレンド判定**: 5秒間のブロック平均により、増加/減少/安定を判定
6. **音声フィードバック**: トレンドに基づいて報酬音または罰音を再生

### トレンド判定アルゴリズム

- **ブロック時間窓**: 5秒
- **判定閾値**: ±1.0 BPM
- **増加トレンド**: 現在のブロック平均 > 前回のブロック平均 + 1.0 BPM
- **減少トレンド**: 現在のブロック平均 < 前回のブロック平均 - 1.0 BPM
- **安定トレンド**: 上記以外

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

---
