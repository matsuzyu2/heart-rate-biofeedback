"""
音声フィードバック制御
"""
import pygame
import logging
from typing import Optional
from pathlib import Path


# ログ設定
logger = logging.getLogger(__name__)


class AudioFeedbackError(Exception):
    """音声フィードバック関連のエラー"""
    pass


class AudioFeedback:
    """
    音声フィードバッククラス
    責任: 報酬音と罰音の再生
    """
    
    def __init__(self, reward_sound: str, punishment_sound: str):
        """
        音声フィードバックの初期化
        
        Args:
            reward_sound: 報酬音のファイルパス
            punishment_sound: 罰音のファイルパス
            
        Raises:
            AudioFeedbackError: 音声ファイルが存在しない場合
        """
        self.reward_sound_path = reward_sound
        self.punishment_sound_path = punishment_sound
        
        # ファイル存在チェック（YAGNI: エラーハンドリングは現在必要）
        self._validate_sound_files()
        
        # pygame mixerの初期化（一度だけ）
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error as e:
            raise AudioFeedbackError(f"Failed to initialize pygame mixer: {e}")
    
    def _validate_sound_files(self) -> None:
        """
        音声ファイルの存在を検証
        
        Raises:
            AudioFeedbackError: ファイルが存在しない場合
        """
        for sound_path in [self.reward_sound_path, self.punishment_sound_path]:
            if not Path(sound_path).exists():
                raise AudioFeedbackError(f"Sound file not found: {sound_path}")
    
    def play_reward(self) -> None:
        """
        報酬音を再生
        
        YAGNI: 現在はシンプルな再生のみ
        将来的に音量制御や重複再生制御が必要になったら追加
        
        Raises:
            AudioFeedbackError: 音声再生に失敗した場合
        """
        try:
            sound = pygame.mixer.Sound(self.reward_sound_path)
            sound.play()
            logger.debug("Reward sound played successfully")
        except pygame.error as e:
            raise AudioFeedbackError(f"Failed to play reward sound: {e}")
    
    def play_punishment(self) -> None:
        """
        罰音を再生
        
        YAGNI: 現在はシンプルな再生のみ
        
        Raises:
            AudioFeedbackError: 音声再生に失敗した場合
        """
        try:
            sound = pygame.mixer.Sound(self.punishment_sound_path)
            sound.play()
            logger.debug("Punishment sound played successfully")
        except pygame.error as e:
            raise AudioFeedbackError(f"Failed to play punishment sound: {e}")
