"""
心拍数データ処理・統計計算
YAGNI原則: 現在必要な機能のみを実装
TDD: テストを通す最小限の実装から開始
"""
from typing import List, Dict, Union


class DataValidator:
    """
    心拍数データの妥当性検証クラス
    単一責任原則（SRP）: データ検証のみを責務とする
    YAGNI: 現在必要な検証ルール（範囲チェック）のみ実装
    """
    
    def __init__(self, min_heart_rate: int = 40, max_heart_rate: int = 220):
        """
        データバリデーターの初期化
        
        Args:
            min_heart_rate: 最低心拍数（デフォルト40 BPM）
            max_heart_rate: 最高心拍数（デフォルト220 BPM）
        """
        self.min_heart_rate = min_heart_rate
        self.max_heart_rate = max_heart_rate
    
    def is_valid(self, heart_rate: int) -> bool:
        """
        心拍数の妥当性をチェック
        
        Args:
            heart_rate: 検証対象の心拍数
            
        Returns:
            bool: 有効な場合True、無効な場合False
        """
        if not isinstance(heart_rate, (int, float)):
            return False
        
        return self.min_heart_rate <= heart_rate <= self.max_heart_rate


class TrendAnalyzer:
    """
    心拍数トレンド分析クラス
    単一責任原則（SRP）: トレンド分析のみを責務とする
    YAGNI: 直近平均 vs 全体平均の比較のみ実装
    """
    
    def __init__(self, recent_window: int = 5, threshold: float = 1.0):
        """
        トレンドアナライザーの初期化
        
        Args:
            recent_window: 直近データの窓サイズ（デフォルト5個）
            threshold: 判定閾値（BPM、デフォルト1.0）
        """
        self.recent_window = recent_window
        self.threshold = threshold
    
    def analyze_trend(self, heart_rates: List[int]) -> str:
        """
        直近平均 vs 全体平均でトレンド判定
        
        Args:
            heart_rates: 心拍数のリスト
            
        Returns:
            str: "increasing" | "decreasing" | "stable"
        """
        # データ不足の場合は安定とみなす
        if len(heart_rates) < self.recent_window + 1:
            return "stable"
        
        # 全体平均を計算
        overall_average = sum(heart_rates) / len(heart_rates)
        
        # 直近データの平均を計算
        recent_data = heart_rates[-self.recent_window:]
        recent_average = sum(recent_data) / len(recent_data)
        
        # 差分で判定
        difference = recent_average - overall_average
        
        if difference > self.threshold:
            return "increasing"
        elif difference < -self.threshold:
            return "decreasing"
        else:
            return "stable"


class HeartRateProcessor:
    """
    心拍数データプロセッサー（メインクラス）
    責任: DataValidatorとTrendAnalyzerの統合・データ管理
    YAGNI: 現在必要な統合機能のみ実装
    """
    
    def __init__(self):
        """心拍数プロセッサーの初期化"""
        self.heart_rates: List[int] = []
        self.validator = DataValidator()
        self.trend_analyzer = TrendAnalyzer()
    
    def add_heart_rate(self, heart_rate: int) -> bool:
        """
        心拍数データを追加
        
        Args:
            heart_rate: 追加する心拍数
            
        Returns:
            bool: 追加に成功した場合True
        """
        if self.validator.is_valid(heart_rate):
            self.heart_rates.append(int(heart_rate))
            return True
        return False
    
    def get_heart_rates(self) -> List[int]:
        """
        保存されている心拍数データを取得
        
        Returns:
            List[int]: 心拍数のリスト
        """
        return self.heart_rates.copy()  # 不変性のためコピーを返す
    
    def get_current_trend(self) -> str:
        """
        現在のトレンドを取得
        
        Returns:
            str: "increasing" | "decreasing" | "stable"
        """
        return self.trend_analyzer.analyze_trend(self.heart_rates)
    
    def get_statistics(self) -> Dict[str, Union[int, float]]:
        """
        基本統計情報を取得
        YAGNI: 現在必要な統計のみ（件数、平均、最新値）
        
        Returns:
            Dict: 統計情報
        """
        if not self.heart_rates:
            return {
                "count": 0,
                "average": 0.0,
                "latest": 0
            }
        
        return {
            "count": len(self.heart_rates),
            "average": sum(self.heart_rates) / len(self.heart_rates),
            "latest": self.heart_rates[-1]
        }


# 【復習課題】
# 問題: 上記のコードで使用されている「依存性注入」のパターンについて説明し、
# なぜHeartRateProcessorクラス内でDataValidatorとTrendAnalyzerのインスタンスを
# 作成しているのか理由を答えてください。
#
# 解答例:
# 依存性注入とは、クラスが依存するオブジェクトを外部から注入する設計パターンです。
# しかし、このコードでは簡略化のため内部でインスタンスを作成しています。
# 理由:
# 1. YAGNI原則: 現在はテスト用モックが不要なため、複雑な注入機構は実装しない
# 2. 単純性: 初期実装では理解しやすさを優先
# 3. 将来の改善: 必要になった時点で外部注入に変更可能
#
# より良い設計（将来の改善例）:
# def __init__(self, validator=None, trend_analyzer=None):
#     self.validator = validator or DataValidator()
#     self.trend_analyzer = trend_analyzer or TrendAnalyzer()
