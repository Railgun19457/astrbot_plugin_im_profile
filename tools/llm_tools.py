from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

import mcp
from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass

from astrbot.api import logger
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext
from astrbot.core.utils.io import download_image_by_url


class _BaseIMProfileTool(FunctionTool[AstrAgentContext]):
    plugin: Any = None

    def _get_event(self, context: ContextWrapper[AstrAgentContext]):
        wrapped_context = getattr(context, "context", None)
        event = getattr(wrapped_context, "event", None)
        if event is not None:
            return event
        return getattr(context, "event", None)

    @staticmethod
    def _as_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()


@pydantic_dataclass
class IMProfileSetProfileTool(_BaseIMProfileTool):
    name: str = "im_profile_set_profile"
    description: str = "修改 Bot 在 QQ 平台上的基础资料（昵称、个性签名、性别）。"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "nickname": {
                    "type": "string",
                    "description": "可选。新的 QQ 昵称。",
                },
                "personal_note": {
                    "type": "string",
                    "description": "可选。新的个性签名。",
                },
                "sex": {
                    "type": "string",
                    "description": "可选。male/female/unknown。",
                },
            },
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs: Any,
    ) -> ToolExecResult:
        plugin = self.plugin
        event = self._get_event(context)
        if not plugin or not event:
            return "修改资料失败，请在消息上下文中重试。"

        nickname = self._as_text(kwargs.get("nickname", ""))
        personal_note = self._as_text(kwargs.get("personal_note", ""))
        sex = self._as_text(kwargs.get("sex", ""))

        return await plugin._run_llm_tool(
            "set_profile",
            lambda: plugin.set_profile(event, nickname, personal_note, sex),
            "修改资料失败，请稍后重试。",
        )


@pydantic_dataclass
class IMProfileSetAvatarTool(_BaseIMProfileTool):
    name: str = "im_profile_set_avatar"
    description: str = "修改 Bot 在 QQ 平台上的头像。"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "avatar_url": {
                    "type": "string",
                    "description": "头像文件 URL 。",
                }
            },
            "required": ["avatar_url"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs: Any,
    ) -> ToolExecResult:
        plugin = self.plugin
        event = self._get_event(context)
        if not plugin or not event:
            return "修改头像失败，请在消息上下文中重试。"

        avatar_url = self._as_text(kwargs.get("avatar_url", ""))
        return await plugin._run_llm_tool(
            "set_avatar",
            lambda: plugin.set_avatar(event, avatar_url),
            "修改头像失败，请稍后重试。",
        )


@pydantic_dataclass
class IMProfileSetGroupCardTool(_BaseIMProfileTool):
    name: str = "im_profile_set_group_card"
    description: str = "修改 Bot 在当前群聊中的 群名片/群昵称。"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "card": {
                    "type": "string",
                    "description": "新的群名片。",
                },
                "group_id": {
                    "type": "string",
                    "description": "可选。目标群号；不填时默认取当前消息所在群。",
                },
            },
            "required": ["card"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs: Any,
    ) -> ToolExecResult:
        plugin = self.plugin
        event = self._get_event(context)
        if not plugin or not event:
            return "修改群名片失败，请在消息上下文中重试。"

        card = self._as_text(kwargs.get("card", ""))
        group_id = self._as_text(kwargs.get("group_id", ""))
        return await plugin._run_llm_tool(
            "set_group_card",
            lambda: plugin.set_group_card(event, card, group_id or None),
            "修改群名片失败，请稍后重试。",
        )


@pydantic_dataclass
class IMProfileGetAvatarTool(_BaseIMProfileTool):
    name: str = "im_profile_get_avatar"
    description: str = "获取 Bot 自身或指定 QQ 用户的头像图片与 URL。"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "可选。目标 QQ 用户 ID，不填时默认查询 Bot 自身。",
                }
            },
        }
    )

    @staticmethod
    async def _build_avatar_image_content(
        avatar_url: str,
    ) -> mcp.types.ImageContent | None:
        temp_path = ""
        try:
            temp_path = await download_image_by_url(avatar_url)
            file_path = Path(temp_path)
            if not file_path.is_file():
                return None

            mime_type = mimetypes.guess_type(avatar_url)[0] or "image/jpeg"
            encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
            return mcp.types.ImageContent(
                type="image",
                data=encoded,
                mimeType=mime_type,
            )
        except Exception:  # noqa: BLE001
            logger.exception("im_profile 获取头像图片失败：url=%s", avatar_url)
            return None
        finally:
            if temp_path:
                path_obj = Path(temp_path)
                if path_obj.is_file():
                    path_obj.unlink(missing_ok=True)

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs: Any,
    ) -> ToolExecResult:
        plugin = self.plugin
        event = self._get_event(context)
        if not plugin or not event:
            return "查询头像失败，请在消息上下文中重试。"

        user_id = self._as_text(kwargs.get("user_id", ""))

        async def _runner() -> ToolExecResult:
            target_user_id, avatar_url, is_self = await plugin.get_avatar_info(
                event,
                user_id or None,
            )

            owner_desc = "机器人自身" if is_self else f"用户 {target_user_id}"
            content: list[mcp.types.TextContent | mcp.types.ImageContent] = [
                mcp.types.TextContent(
                    type="text",
                    text=f"{owner_desc}头像 URL: {avatar_url}",
                )
            ]

            image_content = await self._build_avatar_image_content(avatar_url)
            if image_content is not None:
                content.append(image_content)
            else:
                content.append(
                    mcp.types.TextContent(
                        type="text",
                        text="头像图片下载失败，已返回头像 URL，可继续使用该 URL。",
                    )
                )

            return mcp.types.CallToolResult(content=content)

        return await plugin._run_llm_tool(
            "get_avatar",
            _runner,
            "查询头像失败，请稍后重试。",
        )


def build_llm_tools(plugin) -> list[FunctionTool[AstrAgentContext]]:
    tools: list[FunctionTool[AstrAgentContext]] = [
        IMProfileSetProfileTool(),
        IMProfileSetAvatarTool(),
        IMProfileSetGroupCardTool(),
        IMProfileGetAvatarTool(),
    ]

    # 将插件实例在初始化后注入，避免 dataclass 参数过滤导致 plugin 丢失。
    for tool in tools:
        tool.plugin = plugin

    return tools
