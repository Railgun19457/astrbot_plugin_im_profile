from __future__ import annotations

from collections.abc import Mapping

from astrbot.api.event import AstrMessageEvent

from ..platforms.base import IMProfilePlatformAdapter
from ..platforms.qq_adapter import QQProfileAdapter


class IMProfileService:
    def __init__(
        self,
        adapters: Mapping[str, IMProfilePlatformAdapter] | None = None,
    ) -> None:
        if adapters is None:
            qq_adapter = QQProfileAdapter()
            adapters = {"aiocqhttp": qq_adapter}
        self._adapters = dict(adapters)

    def _resolve_adapter(self, event: AstrMessageEvent) -> IMProfilePlatformAdapter:
        platform_name = str(event.get_platform_name() or "").strip().lower()
        if not platform_name:
            raise RuntimeError("无法识别当前消息平台。")
        adapter = self._adapters.get(platform_name)
        if adapter is None:
            raise RuntimeError(
                f"暂不支持平台 {platform_name}。当前仅支持 QQ(aiocqhttp)。"
            )
        return adapter

    async def set_profile(
        self,
        event: AstrMessageEvent,
        nickname: str,
        personal_note: str,
        sex: str,
    ) -> str:
        adapter = self._resolve_adapter(event)
        await adapter.set_profile(
            event=event,
            nickname=nickname,
            personal_note=personal_note,
            sex=sex,
        )

        changed_items: list[str] = []
        if nickname:
            changed_items.append("昵称")
        if personal_note:
            changed_items.append("资料签名")
        if sex:
            changed_items.append("性别")

        suffix = f"（{', '.join(changed_items)}）" if changed_items else ""
        return f"资料已更新{suffix}。"

    async def set_avatar(self, event: AstrMessageEvent, avatar_url: str) -> str:
        adapter = self._resolve_adapter(event)
        await adapter.set_avatar(event=event, avatar_url=avatar_url)
        return "头像已更新。"

    async def set_signature(self, event: AstrMessageEvent, signature: str) -> str:
        adapter = self._resolve_adapter(event)
        await adapter.set_signature(event=event, signature=signature)
        return "个性签名已更新。"

    async def set_group_card(
        self,
        event: AstrMessageEvent,
        card: str,
        group_id: str | None,
    ) -> str:
        adapter = self._resolve_adapter(event)
        await adapter.set_group_card(event=event, card=card, group_id=group_id)

        target_group_id = (group_id or "").strip() or str(
            event.get_group_id() or ""
        ).strip()
        if not target_group_id:
            raise ValueError("当前消息不在群聊中，且未提供 group_id。")
        return f"个人群名片已更新（群 {target_group_id}）。"

    def resolve_avatar(
        self,
        event: AstrMessageEvent,
        user_id: str | None,
    ) -> tuple[str, str, bool]:
        adapter = self._resolve_adapter(event)
        requested_user_id = (user_id or "").strip()
        target_user_id = requested_user_id or str(event.get_self_id() or "").strip()
        if not target_user_id:
            raise ValueError("无法获取目标用户 ID，请显式传入 user_id。")

        avatar_url = adapter.get_avatar_url(target_user_id)
        return target_user_id, avatar_url, not bool(requested_user_id)

    async def get_avatar_url(self, event: AstrMessageEvent, user_id: str | None) -> str:
        target_user_id, avatar_url, is_self = self.resolve_avatar(event, user_id)
        if not is_self:
            return f"用户 {target_user_id} 的头像 URL: {avatar_url}"
        return f"机器人自身头像 URL: {avatar_url}"
