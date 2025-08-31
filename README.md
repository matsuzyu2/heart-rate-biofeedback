# Heart Rate Biofeedback System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()

リアルタイム心拍数監視による音声バイオフィードバック実験システムです。Polar H9/H10心拍センサーを使用して、心拍数の意識的なコントロール能力を測定・訓練します。

## 🎯 概要

このシステムは心拍数バイオフィードバック実験のために設計されました。被験者は3つの異なるモードで心拍数をコントロールし、その能力を測定・向上させることができます。

### 主な特徴

- 🫀 **リアルタイム心拍数監視**: Polar H9/H10センサーによる高精度測定
- 🔊 **即座の音声フィードバック**: 100ms以下の低遅延応答
- 📊 **3つの実験モード**: 増加報酬・減少報酬・ランダム制御
- 📈 **データ記録**: 高精度タイムスタンプ付きセッションログ
- 🛡️ **安全機能**: 異常検知と自動停止機能

## 🚀 クイックスタート

### 必要要件

- Python 3.11以上
- Polar H9またはH10心拍センサー
- Bluetooth対応デバイス
- macOS / Linux / Windows

### インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/your-username/heart-rate-biofeedback.git
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
python src/main.py --mode increase

# 心拍数減少報酬モード  
python src/main.py --mode decrease

# ランダム制御モード
python src/main.py --mode random
```

3. **実験終了**:
   - `Ctrl+C`で安全に終了
   - セッションデータは自動保存

## 📋 実験モード

### 1. 増加報酬モード (`--mode increase`)
- 心拍数が増加すると報酬音が再生
- 心拍数上昇の意識的コントロールを訓練

### 2. 減少報酬モード (`--mode decrease`)  
- 心拍数が減少すると報酬音が再生
- リラクゼーション・瞑想効果を測定

### 3. ランダム制御モード (`--mode random`)
- ランダムなタイミングで音声再生
- 制御群としての比較データ取得

## 🔧 設定

### センサー設定
```python
# src/config/sensor_config.py で調整可能
DEVICE_NAME_FILTER = "Polar"
CONNECTION_TIMEOUT = 10
RETRY_ATTEMPTS = 3
```

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

---
