from __future__ import annotations

from abc import ABC, abstractmethod

from astrbot.api.event import AstrMessageEvent


class IMProfilePlatformAdapter(ABC):
    platform_name: str

    @abstractmethod
    async def set_profile(
        self,
        event: AstrMessageEvent,
        nickname: str,
        personal_note: str,
        sex: str,
    ) -> None:
        pass

    @abstractmethod
    async def set_avatar(self, event: AstrMessageEvent, avatar_url: str) -> None:
        pass

    @abstractmethod
    async def set_signature(self, event: AstrMessageEvent, signature: str) -> None:
        pass

    @abstractmethod
    async def set_group_card(
        self,
        event: AstrMessageEvent,
        card: str,
        group_id: str | None,
    ) -> None:
        pass

    @abstractmethod
    def get_avatar_url(self, user_id: str) -> str:
        pass
