"""
フィードバックモード実装
開放閉鎖原則（OCP）: 新しいモードの追加が容易
リスコフ置換原則（LSP）: 基底クラスの置き換えが可能
YAGNI原則: 現在必要な3モードのみ実装
"""
from abc import ABC, abstractmethod
import random
from typing import Protocol


class AudioFeedbackProtocol(Protocol):
    """
    音声フィードバックのプロトコル（インターフェース分離原則）
    """
    def play_reward(self) -> None:
        """報酬音を再生"""
        ...
    
    def play_punishment(self) -> None:
        """罰音を再生"""
        ...


class FeedbackMode(ABC):
    """
    フィードバックモードの抽象基底クラス
    """
    
    def __init__(self, audio_feedback: AudioFeedbackProtocol):
        """
        フィードバックモードの初期化
        
        Args:
            audio_feedback: 音声フィードバックインターフェース
        """
        self.audio_feedback = audio_feedback
    
    @abstractmethod
    def process_feedback(self, trend: str) -> None:
        """
        トレンドに基づいてフィードバックを処理
        
        Args:
            trend: "increasing", "decreasing", "stable"
        """
        pass


class IncreaseRewardMode(FeedbackMode):
    """
    増加報酬モード
    """
    
    def process_feedback(self, trend: str) -> None:
        """
        心拍数増加で報酬、減少で罰を与える
        
        Args:
            trend: 心拍数のトレンド
        """
        if trend == "increasing":
            self.audio_feedback.play_reward()
        elif trend == "decreasing":
            self.audio_feedback.play_punishment()
        # "stable"の場合は何もしない（YAGNI: 現在は安定時の処理不要）


class DecreaseRewardMode(FeedbackMode):
    """
    減少報酬モード
    """
    
    def process_feedback(self, trend: str) -> None:
        """
        心拍数減少で報酬、増加で罰を与える
        
        Args:
            trend: 心拍数のトレンド
        """
        if trend == "decreasing":
            self.audio_feedback.play_reward()
        elif trend == "increasing":
            self.audio_feedback.play_punishment()
        # "stable"の場合は何もしない


class RandomMode(FeedbackMode):
    """
    ランダムモード（対照群）
    """
    
    def process_feedback(self, trend: str) -> None:
        """
        トレンドに関係なくランダムにフィードバックを与える
        
        Args:
            trend: 心拍数のトレンド（このモードでは使用しない）
        """
        # YAGNI: 現在は50%の確率でシンプルに実装
        feedback_type = random.choice(['reward', 'punishment'])
        
        if feedback_type == 'reward':
            self.audio_feedback.play_reward()
        else:
            self.audio_feedback.play_punishment()
