from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import unquote, urlparse

from astrbot.api.event import AstrMessageEvent

from .base import IMProfilePlatformAdapter


class QQProfileAdapter(IMProfilePlatformAdapter):
    platform_name = "aiocqhttp"
    _AVATAR_URL_TEMPLATE = "https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"
    _SEX_MAP = {
        "male": "male",
        "m": "male",
        "男": "male",
        "female": "female",
        "f": "female",
        "女": "female",
        "unknown": "unknown",
        "unk": "unknown",
        "未知": "unknown",
    }

    @staticmethod
    def _get_client(event: AstrMessageEvent):
        bot = getattr(event, "bot", None)
        api = getattr(bot, "api", None)
        if bot is None or api is None:
            raise RuntimeError("当前事件未提供 QQ 协议客户端，无法调用 NapCat API。")
        return bot

    @classmethod
    def _normalize_sex(cls, sex: str) -> str:
        normalized = sex.strip().lower()
        if not normalized:
            return ""
        mapped = cls._SEX_MAP.get(normalized)
        if mapped is None:
            raise ValueError("sex 仅支持 male/female/unknown。")
        return mapped

    @staticmethod
    def _parse_numeric_id(value: str | int | None, field_name: str) -> int:
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"{field_name} 不能为空。")
        if not text.isdigit():
            raise ValueError(f"{field_name} 必须为数字。")
        return int(text)

    @staticmethod
    def _normalize_windows_drive_prefix(path_text: str) -> str:
        normalized = path_text.strip()
        if (
            len(normalized) > 2
            and normalized[0] == "/"
            and normalized[1].isalpha()
            and normalized[2] == ":"
        ):
            return normalized[1:]
        return normalized

    @classmethod
    def _resolve_local_avatar_path(cls, avatar_url: str) -> Path | None:
        text = avatar_url.strip()
        if not text:
            return None

        lowered = text.lower()
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return None
        if lowered.startswith("base64://"):
            return None

        parsed = urlparse(text)
        if parsed.scheme == "file":
            raw_path = unquote(parsed.path or "")
            raw_path = cls._normalize_windows_drive_prefix(raw_path)
            if parsed.netloc and parsed.netloc.lower() != "localhost":
                if (
                    len(parsed.netloc) == 2
                    and parsed.netloc[0].isalpha()
                    and parsed.netloc[1] == ":"
                ):
                    raw_path = cls._normalize_windows_drive_prefix(
                        f"{parsed.netloc}{raw_path}"
                    )
                else:
                    raw_path = f"//{parsed.netloc}{raw_path}"
            return Path(raw_path).expanduser().resolve()

        if "://" in text:
            return None

        raw_path = cls._normalize_windows_drive_prefix(text)
        return Path(raw_path).expanduser().resolve()

    @staticmethod
    async def _resolve_required_nickname(client, nickname: str) -> str:
        nickname_text = nickname.strip()
        if nickname_text:
            return nickname_text

        login_info = await client.api.call_action("get_login_info")
        resolved_nickname = ""

        if isinstance(login_info, dict):
            resolved_nickname = str(login_info.get("nickname", "")).strip()
            if not resolved_nickname:
                data = login_info.get("data")
                if isinstance(data, dict):
                    resolved_nickname = str(data.get("nickname", "")).strip()

        if not resolved_nickname:
            raise ValueError("nickname 不能为空，且无法自动获取当前昵称。")
        return resolved_nickname

    async def set_profile(
        self,
        event: AstrMessageEvent,
        nickname: str,
        personal_note: str,
        sex: str,
    ) -> None:
        nickname_text = nickname.strip()
        personal_note_text = personal_note.strip()
        sex_text = sex.strip()

        if not (nickname_text or personal_note_text or sex_text):
            raise ValueError("请至少提供一个待更新字段：nickname/personal_note/sex。")

        client = self._get_client(event)
        required_nickname = await self._resolve_required_nickname(client, nickname_text)

        payload: dict[str, str] = {"nickname": required_nickname}
        if personal_note_text:
            payload["personal_note"] = personal_note_text
        if sex_text:
            payload["sex"] = self._normalize_sex(sex_text)

        await client.api.call_action("set_qq_profile", **payload)

    async def set_avatar(self, event: AstrMessageEvent, avatar_url: str) -> None:
        url_text = avatar_url.strip()
        if not url_text:
            raise ValueError("avatar_url 不能为空。")

        client = self._get_client(event)
        local_path = self._resolve_local_avatar_path(url_text)

        if local_path is None:
            await client.api.call_action("set_qq_avatar", file=url_text)
            return

        if not local_path.is_file():
            raise ValueError(f"头像文件不存在：{local_path.as_posix()}")

        encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")
        await client.api.call_action("set_qq_avatar", file=f"base64://{encoded}")

    async def set_signature(self, event: AstrMessageEvent, signature: str) -> None:
        long_nick = signature.strip()
        if not long_nick:
            raise ValueError("signature 不能为空。")

        client = self._get_client(event)
        await client.api.call_action("set_self_longnick", longNick=long_nick)

    async def set_group_card(
        self,
        event: AstrMessageEvent,
        card: str,
        group_id: str | None,
    ) -> None:
        card_text = card.strip()
        if not card_text:
            raise ValueError("card 不能为空。")

        event_group_id = str(event.get_group_id() or "").strip()
        target_group_id = (group_id or "").strip() or event_group_id
        if not target_group_id:
            raise ValueError("当前消息不在群聊中，且未提供 group_id。")

        self_id = str(event.get_self_id() or "").strip()
        group_id_num = self._parse_numeric_id(target_group_id, "group_id")
        self_id_num = self._parse_numeric_id(self_id, "self_id")

        client = self._get_client(event)
        await client.api.call_action(
            "set_group_card",
            group_id=group_id_num,
            user_id=self_id_num,
            card=card_text[:60],
        )

    def get_avatar_url(self, user_id: str) -> str:
        qq_user_id = str(user_id).strip()
        if not qq_user_id:
            raise ValueError("user_id 不能为空。")
        if not qq_user_id.isdigit():
            raise ValueError("QQ user_id 必须为数字。")
        return self._AVATAR_URL_TEMPLATE.format(user_id=qq_user_id)
