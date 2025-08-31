# コーディング規約

## 命名規則

### 変数・関数名
- **形式**: snake_case
- **明確性**: 略語を避け、意図が明確な名前
- **例**:
  ```python
  # Good
  heart_rate_threshold = 80
  def calculate_average_heart_rate():
  
  # Bad
  hr_th = 80
  def calc_avg_hr():
  ```

### クラス名
- **形式**: PascalCase
- **意味**: 責任を表す名詞
- **例**:
  ```python
  # Good
  class HeartRateProcessor:
  class AudioFeedbackController:
  
  # Bad
  class processor:
  class audio:
  ```

### 定数
- **形式**: UPPER_SNAKE_CASE
- **配置**: モジュールトップレベルまたは設定ファイル
- **例**:
  ```python
  MAX_HEART_RATE = 200
  FEEDBACK_DELAY_MS = 100
  POLAR_H10_SERVICE_UUID = "180D"
  ```

### ファイル・モジュール名
- **形式**: snake_case
- **明確性**: 機能を表す名前
- **例**: `heart_rate_processor.py`, `audio_feedback.py`

## コード構造

### インポート順序
1. 標準ライブラリ
2. サードパーティライブラリ
3. ローカルモジュール

```python
# 標準ライブラリ
import asyncio
import logging
from typing import Optional, List

# サードパーティライブラリ
import numpy as np
from bleak import BleakClient

# ローカルモジュール
from src.sensor.polar_h10_interface import PolarH10Interface
from src.processing.heart_rate_processor import HeartRateProcessor
```

### 関数・メソッド設計
- **長さ**: 1つの関数は50行以内を目標
- **責任**: 単一の責任を持つ
- **引数**: 5個以内を推奨
- **戻り値**: 型ヒントを必須

```python
def process_heart_rate_data(
    raw_data: bytes,
    timestamp: float,
    baseline_hr: int = 60
) -> Optional[int]:
    """心拍数データを処理して心拍数を返す
    
    Args:
        raw_data: センサーからの生データ
        timestamp: データ取得時刻
        baseline_hr: ベースライン心拍数
        
    Returns:
        処理済み心拍数、エラー時はNone
    """
```

### クラス設計
- **継承**: 深い継承階層を避ける（3レベル以内）
- **責任**: 単一責任原則を遵守
- **インターフェース**: プロトコルを活用した型安全性

```python
from typing import Protocol

class HeartRateSensor(Protocol):
    """心拍センサーのインターフェース"""
    
    async def connect(self) -> bool:
        """センサーに接続"""
        ...
    
    async def get_heart_rate(self) -> Optional[int]:
        """心拍数を取得"""
        ...
```

## エラーハンドリング

### 例外処理方針
- **具体的な例外**: 汎用的なExceptionを避ける
- **適切なレベル**: 処理可能なレベルでキャッチ
- **ログ記録**: 例外発生時の詳細な情報記録

```python
import logging

logger = logging.getLogger(__name__)

try:
    heart_rate = await sensor.get_heart_rate()
except ConnectionError as e:
    logger.error(f"センサー接続エラー: {e}")
    await sensor.reconnect()
except ValueError as e:
    logger.warning(f"無効な心拍数データ: {e}")
    return None
```

### カスタム例外
```python
class HeartRateError(Exception):
    """心拍関連のエラー基底クラス"""
    pass

class SensorConnectionError(HeartRateError):
    """センサー接続エラー"""
    pass

class InvalidHeartRateError(HeartRateError):
    """無効な心拍数値エラー"""
    pass
```

## ドキュメンテーション

### docstring規約
- **形式**: Google Style
- **必須項目**: Args, Returns, Raises
- **例**:

```python
def calculate_heart_rate_trend(
    heart_rates: List[int],
    window_size: int = 5
) -> str:
    """心拍数のトレンドを計算
    
    指定されたウィンドウサイズで心拍数の傾向を分析し、
    増加、減少、安定のいずれかを返す。
    
    Args:
        heart_rates: 心拍数のリスト
        window_size: 分析に使用するデータ点数
        
    Returns:
        "increasing", "decreasing", "stable"のいずれか
        
    Raises:
        ValueError: heart_ratesが空または無効な場合
        
    Example:
        >>> calculate_heart_rate_trend([70, 72, 75, 78])
        "increasing"
    """
```

## 品質保証

### 型ヒント
- **必須**: 全ての関数・メソッドに型ヒント
- **推奨**: 変数にも型ヒント（複雑な場合）

```python
from typing import Dict, List, Optional, Union

def analyze_session_data(
    session_data: Dict[str, List[int]],
    mode: str
) -> Optional[Dict[str, Union[float, int]]]:
    """セッションデータを分析"""
```

### ログ出力
- **レベル**: DEBUG, INFO, WARNING, ERROR, CRITICALを適切に使用
- **内容**: 実行状況、エラー詳細、パフォーマンス情報

```python
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 使用例
logger.info("セッション開始: モード=%s", mode_name)
logger.debug("心拍数取得: %d bpm", heart_rate)
logger.warning("心拍数異常値検出: %d bpm", abnormal_rate)
logger.error("センサー接続失敗: %s", error_message)
```

### テスタビリティ
- **依存性注入**: テスト用モックの注入を容易に
- **純粋関数**: 副作用のない関数を優先
- **設定外部化**: ハードコードを避ける

```python
class HeartRateAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.threshold = config["threshold"]
        self.window_size = config["window_size"]
    
    def analyze(self, data: List[int]) -> str:
        # 純粋関数として実装
        return self._calculate_trend(data, self.window_size)
```
