# テストガイドライン

## テスト駆動開発 (TDD)

### YAGNI原則に基づくテスト戦略

#### YAGNI ("You Aren't Gonna Need It") のテスト適用
- **基本思想**: 現在実装されている機能のみをテスト対象とする
- **判断基準**: 「将来追加予定の機能」「仕様にない機能」はテスト対象外
- **効果**: テスト作成・保守コストの最適化、重要なテストに集中

#### 具体的なテスト指針
- **必要最低限**: 現在の要件に対してのみテストを作成
- **過剰テスト回避**: 将来必要になるかもしれない機能のテストは作成しない
- **実用性重視**: 実際にバグを検出できるテストに集中
- **段階的拡張**: 機能追加時に対応するテストも追加

#### YAGNI適用例
```python
# ❌ YAGNI違反: 未実装機能のテスト
def test_future_sensor_types():
    """まだ対応していないセンサータイプのテスト"""
    # Polar H10以外のセンサーはまだ対応していないのにテストを作成
    pass

# ✅ YAGNI準拠: 実装済み機能のテスト
def test_polar_h9_heart_rate_processing():
    """実際に使用するPolar H9の心拍数処理テスト"""
    processor = HeartRateDataProcessor()
    raw_data = b'\x16\x4e\x00'  # 実際のH9データ形式
    result = processor.process(raw_data)
    assert result == 78
```

#### テスト範囲の決定基準
- **現在実装**: 100%テストカバレッジを目指す
- **計画中機能**: テスト作成は実装後
- **推測機能**: 実際に必要になるまでテスト不要
- **エラーハンドリング**: 現実的に発生するエラーのみテスト

### Red-Green-Refactor サイクル
1. **Red**: 失敗するテストを書く
2. **Green**: テストを通す最小限のコードを書く
3. **Refactor**: コードの品質を向上させる

### テスト駆動開発の基本原則
- **テスト失敗時の対応**: テストに通らない場合は、テストコードを修正するのではなく、実装コードを修正する
- **変更時の順序**: リファクタリングや機能追加を行う際は、先にテストコードを修正してから実装コードを変更する
- **テストの信頼性**: テストコードは仕様書として機能するため、安易に修正しない
- **実装の検証**: 実装がテストに合わせるべきであり、その逆ではない

### TDD 実践例
```python
# 1. Red: 失敗するテストを書く（仕様を定義）
def test_calculate_heart_rate_trend_increasing():
    """心拍数増加トレンドのテスト"""
    heart_rates = [70, 72, 75, 78, 80]
    result = calculate_heart_rate_trend(heart_rates)
    assert result == "increasing"

# 2. Green: 最小限の実装（テストを通すため）
def calculate_heart_rate_trend(heart_rates):
    return "increasing"  # とりあえず通すだけ

# 3. Refactor: 正しい実装に改善（テストが保証）
def calculate_heart_rate_trend(heart_rates):
    if len(heart_rates) < 2:
        return "stable"
    
    trend = heart_rates[-1] - heart_rates[0]
    if trend > 2:
        return "increasing"
    elif trend < -2:
        return "decreasing"
    else:
        return "stable"

# 重要: テスト失敗時は実装を修正、テストは修正しない
# 機能追加時は先にテストを更新してから実装を変更
```

## テスト戦略

### テストピラミッド
```
    E2E Tests (少数)
        ↑
  Integration Tests (中程度)
        ↑
    Unit Tests (多数)
```

### テスト分類

#### 単体テスト (Unit Tests) - YAGNI適用
- **対象**: 現在実装されている関数・メソッド・クラスのみ
- **特徴**: 高速、独立、決定的
- **最低限の要件**: 重要なビジネスロジックと境界値のテスト
- **カバレッジ**: 実装済み機能の80%以上を目標（未実装機能は対象外）

```python
import pytest
from unittest.mock import Mock, patch

class TestHeartRateProcessor:
    def test_process_valid_data(self):
        """有効なデータの処理テスト"""
        processor = HeartRateProcessor()
        raw_data = b'\x16\x4e\x00'  # 78 bpm
        
        result = processor.process(raw_data)
        
        assert result == 78
    
    def test_process_invalid_data(self):
        """無効なデータの処理テスト"""
        processor = HeartRateProcessor()
        
        with pytest.raises(ValueError):
            processor.process(b'invalid')
```

#### 統合テスト (Integration Tests) - 必要最低限
- **対象**: 実際に連携する予定のモジュール間の相互作用のみ
- **特徴**: システムの一部分の結合テスト
- **重点**: 実際のデータフローが発生する箇所に限定

```python
@pytest.mark.asyncio
async def test_sensor_to_processor_integration():
    """センサーからプロセッサーまでの統合テスト"""
    # モックセンサーを使用
    mock_sensor = Mock()
    mock_sensor.get_heart_rate.return_value = 75
    
    processor = HeartRateProcessor()
    feedback = AudioFeedback()
    
    # 統合的な動作テスト
    heart_rate = await mock_sensor.get_heart_rate()
    trend = processor.calculate_trend([70, 72, 75])
    feedback_type = feedback.determine_feedback(trend, "increase_reward")
    
    assert heart_rate == 75
    assert trend == "increasing"
    assert feedback_type == "reward"
```

#### エンドツーエンドテスト (E2E Tests) - 最小限実装
- **対象**: 現在の主要ユースケースのみ
- **特徴**: 実際の使用シナリオ
- **限定**: 実装済みの3つのフィードバックモードの基本動作確認のみ

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_biofeedback_session():
    """完全なバイオフィードバックセッションのテスト"""
    # テスト用設定
    config = {
        "mode": "increase_reward",
        "duration": 10,  # 10秒の短縮セッション
        "use_mock_sensor": True
    }
    
    session = BiofeedbackSession(config)
    
    # セッション実行
    results = await session.run()
    
    # 結果検証
    assert results["status"] == "completed"
    assert len(results["heart_rates"]) > 0
    assert results["feedback_count"] >= 0
```

## テスト環境設定

### pytest 設定 (pytest.ini)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers = 
    unit: 単体テスト
    integration: 統合テスト
    e2e: エンドツーエンドテスト
    slow: 実行時間の長いテスト
asyncio_mode = auto
```

### フィクスチャ活用
```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def heart_rate_data():
    """テスト用心拍数データ"""
    return [70, 72, 75, 73, 78, 80, 77, 79, 82, 84]

@pytest.fixture
async def mock_sensor():
    """モックセンサー"""
    sensor = AsyncMock()
    sensor.connect.return_value = True
    sensor.get_heart_rate.return_value = 75
    return sensor

@pytest.fixture
def temp_audio_file(tmp_path):
    """一時音声ファイル"""
    audio_file = tmp_path / "test_audio.wav"
    # テスト用音声データを作成
    create_test_audio(audio_file)
    return audio_file
```

## モック・スタブ戦略

### 外部依存のモック化
```python
from unittest.mock import patch, MagicMock

class TestPolarH10Interface:
    @patch('bleak.BleakClient')
    async def test_connect_success(self, mock_bleak):
        """接続成功テスト"""
        # BLEクライアントのモック設定
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_bleak.return_value = mock_client
        
        sensor = PolarH10Interface("AA:BB:CC:DD:EE:FF")
        result = await sensor.connect()
        
        assert result is True
        mock_client.connect.assert_called_once()
    
    @patch('pygame.mixer.Sound')
    def test_audio_feedback(self, mock_sound):
        """音声フィードバックテスト"""
        mock_sound_instance = MagicMock()
        mock_sound.return_value = mock_sound_instance
        
        feedback = AudioFeedback()
        feedback.play_reward_sound()
        
        mock_sound_instance.play.assert_called_once()
```

### 非同期処理のテスト
```python
@pytest.mark.asyncio
async def test_real_time_processing():
    """リアルタイム処理のテスト"""
    processor = HeartRateProcessor()
    
    # 非同期データストリームのシミュレーション
    async def mock_data_stream():
        for rate in [70, 72, 75, 78]:
            yield rate
            await asyncio.sleep(0.1)
    
    results = []
    async for heart_rate in mock_data_stream():
        trend = processor.update(heart_rate)
        results.append(trend)
    
    assert len(results) == 4
    assert results[-1] == "increasing"
```

## テストデータ管理

### テストケース設計
```python
@pytest.mark.parametrize("heart_rates,expected_trend", [
    ([70, 72, 75, 78], "increasing"),
    ([80, 77, 74, 71], "decreasing"),
    ([75, 76, 75, 74], "stable"),
    ([70], "stable"),  # 単一データ点
    ([], "stable"),    # 空のデータ
])
def test_heart_rate_trend_calculation(heart_rates, expected_trend):
    """心拍数トレンド計算のパラメータ化テスト"""
    result = calculate_heart_rate_trend(heart_rates)
    assert result == expected_trend
```

### テストユーティリティ
```python
def create_test_heart_rate_sequence(
    base_rate: int = 70,
    trend: str = "increasing",
    length: int = 10,
    noise_level: float = 0.1
) -> List[int]:
    """テスト用心拍数シーケンス生成"""
    import random
    
    rates = []
    for i in range(length):
        if trend == "increasing":
            rate = base_rate + i * 2
        elif trend == "decreasing":
            rate = base_rate - i * 2
        else:  # stable
            rate = base_rate
        
        # ノイズ追加
        noise = random.uniform(-noise_level, noise_level) * rate
        rates.append(int(rate + noise))
    
    return rates
```

## カバレッジとレポート

### カバレッジ測定
```bash
# カバレッジ付きテスト実行
pytest --cov=src --cov-report=html

# 特定モジュールのカバレッジ
pytest --cov=src.sensor --cov-report=term-missing

# 統合・E2Eテストの除外
pytest --cov=src tests/unit/
```

### 品質ゲート - YAGNI準拠
- **単体テストカバレッジ**: 実装済み機能の80%以上
- **統合テストカバレッジ**: 実際の連携部分の60%以上
- **重要機能カバレッジ**: 現在の仕様で必須の機能（センサー通信、安全機能）は100%
- **未実装機能**: テスト対象外（将来的に必要になった時点で追加）

### 継続的テスト
```yaml
# GitHub Actions例
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run tests
        run: pytest --cov=src --cov-fail-under=80
```
