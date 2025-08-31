"""
processingモジュールのテストコード
YAGNI原則: 現在必要な機能のみをテスト対象とする
TDD: Red-Green-Refactorサイクルで実装
"""
import unittest
import sys
import os

# テスト対象のインポート（相対インポート）
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.processing.heart_rate_processor import (
    HeartRateProcessor,
    DataValidator, 
    TrendAnalyzer
)


class TestDataValidator(unittest.TestCase):
    """
    データ検証クラスのテスト
    単一責任原則（SRP）: データの妥当性チェックのみを責務とする
    YAGNI: 現在必要な検証ルールのみをテスト
    """
    
    def setUp(self):
        """各テストの前に実行される初期化"""
        self.validator = DataValidator()
    
    def test_有効な心拍数(self):
        """正常な心拍数の検証をテスト"""
        # Red: 最初は失敗する（メソッド未実装のため）
        self.assertTrue(self.validator.is_valid(70))
        self.assertTrue(self.validator.is_valid(100))
        self.assertTrue(self.validator.is_valid(180))
    
    def test_無効な心拍数_範囲外(self):
        """範囲外心拍数の検証をテスト"""
        self.assertFalse(self.validator.is_valid(30))   # 低すぎる
        self.assertFalse(self.validator.is_valid(250))  # 高すぎる
        self.assertFalse(self.validator.is_valid(0))    # ゼロ
        self.assertFalse(self.validator.is_valid(-10))  # 負の値
    
    def test_境界値(self):
        """境界値のテスト"""
        # YAGNI: 現実的な範囲のみをテスト（40-220 BPM）
        self.assertTrue(self.validator.is_valid(40))    # 下限
        self.assertTrue(self.validator.is_valid(220))   # 上限
        self.assertFalse(self.validator.is_valid(39))   # 下限-1
        self.assertFalse(self.validator.is_valid(221))  # 上限+1


class TestTrendAnalyzer(unittest.TestCase):
    """
    トレンド分析クラスのテスト
    単一責任原則（SRP）: トレンド分析のみを責務とする
    YAGNI: 現在必要な分析手法（直近平均 vs 全体平均）のみをテスト
    """
    
    def setUp(self):
        """各テストの前に実行される初期化"""
        self.analyzer = TrendAnalyzer()
    
    def test_増加トレンド(self):
        """心拍数増加トレンドの判定をテスト"""
        # 直近5個の平均が全体平均より高い場合
        # [70,71,72,73,74,78,80,82,84,85] → 全体平均:76.9, 直近平均:81.8
        heart_rates = [70, 71, 72, 73, 74, 78, 80, 82, 84, 85]
        result = self.analyzer.analyze_trend(heart_rates)
        self.assertEqual(result, "increasing")
    
    def test_減少トレンド(self):
        """心拍数減少トレンドの判定をテスト"""
        # 直近5個の平均が全体平均より低い場合
        # [85,84,82,80,78,74,73,71,72,70] → 全体平均:76.9, 直近平均:72.0
        heart_rates = [85, 84, 82, 80, 78, 74, 73, 71, 72, 70]
        result = self.analyzer.analyze_trend(heart_rates)
        self.assertEqual(result, "decreasing")
    
    def test_安定トレンド(self):
        """心拍数安定トレンドの判定をテスト"""
        # 直近5個の平均と全体平均がほぼ同じ場合
        heart_rates = [75, 76, 74, 75, 77, 74, 76, 75, 76, 75]
        result = self.analyzer.analyze_trend(heart_rates)
        self.assertEqual(result, "stable")
    
    def test_データ不足(self):
        """データが不足している場合のテスト"""
        # YAGNI: 直近5個 + 全体計算のため、最低6個必要
        insufficient_data = [70, 72, 75]  # 3個のみ
        result = self.analyzer.analyze_trend(insufficient_data)
        self.assertEqual(result, "stable")
    
    def test_空データ(self):
        """空のデータリストのテスト"""
        result = self.analyzer.analyze_trend([])
        self.assertEqual(result, "stable")


class TestHeartRateProcessor(unittest.TestCase):
    """
    メイン心拍数プロセッサーのテスト
    責任: データバリデーターとトレンドアナライザーの統合
    YAGNI: 現在必要な統合機能のみをテスト
    """
    
    def setUp(self):
        """各テストの前に実行される初期化"""
        self.processor = HeartRateProcessor()
    
    def test_心拍数データ追加(self):
        """有効な心拍数データの追加をテスト"""
        self.processor.add_heart_rate(75)
        self.processor.add_heart_rate(78)
        
        # 追加されたデータが保存されていることを確認
        heart_rates = self.processor.get_heart_rates()
        self.assertEqual(len(heart_rates), 2)
        self.assertEqual(heart_rates, [75, 78])
    
    def test_無効データ拒否(self):
        """無効な心拍数データが拒否されることをテスト"""
        # 無効なデータは追加されない
        self.processor.add_heart_rate(300)  # 無効
        self.processor.add_heart_rate(75)   # 有効
        self.processor.add_heart_rate(-10)  # 無効
        
        heart_rates = self.processor.get_heart_rates()
        self.assertEqual(len(heart_rates), 1)
        self.assertEqual(heart_rates[0], 75)
    
    def test_現在のトレンド取得(self):
        """現在のトレンド取得をテスト"""
        # 増加パターンのデータを追加
        for hr in [70, 71, 72, 73, 74, 78, 80, 82, 84, 85]:
            self.processor.add_heart_rate(hr)
        
        trend = self.processor.get_current_trend()
        self.assertEqual(trend, "increasing")
    
    def test_統計情報取得(self):
        """基本統計情報の取得をテスト"""
        # YAGNI: 現在必要な統計のみ（平均、最新値、データ数）
        for hr in [70, 75, 80]:
            self.processor.add_heart_rate(hr)
        
        stats = self.processor.get_statistics()
        
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["average"], 75.0)
        self.assertEqual(stats["latest"], 80)


if __name__ == '__main__':
    # テスト実行時の使用例を表示
    print("🧪 Processing モジュールテスト（YAGNI準拠・TDD）")
    print("=" * 50)
    print("現在実装対象:")
    print("  ✅ DataValidator: 心拍数妥当性チェック")
    print("  ✅ TrendAnalyzer: 直近平均 vs 全体平均分析")
    print("  ✅ HeartRateProcessor: データ統合・管理")
    print()
    print("YAGNI原則により実装しない:")
    print("  ❌ 高度な統計計算（標準偏差、分散など）")
    print("  ❌ 複雑なフィルタリング（カルマンフィルタなど）")
    print("  ❌ 将来的な拡張機能")
    print("=" * 50)
    
    unittest.main(verbosity=2)