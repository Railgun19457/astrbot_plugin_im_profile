from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.agent.tool import ToolExecResult

from .core.config import IMProfileSettings, load_settings
from .core.profile_service import IMProfileService
from .tools import build_llm_tools


class IMProfilePlugin(Star):
    LLM_TOOL_NAME_BY_OPTION = {
        "profile": "im_profile_set_profile",
        "avatar": "im_profile_set_avatar",
        "group_card": "im_profile_set_group_card",
        "avatar_lookup": "im_profile_get_avatar",
    }

    def __init__(self, context: Context, config: dict[str, Any] | None = None):
        super().__init__(context)
        self.context = context
        self.config: dict[str, Any] = config or {}

        self.settings: IMProfileSettings = IMProfileSettings(llm_tool_options=set())
        self.llm_tool_options: set[str] = set()
        self.profile_service = IMProfileService()

        self.context.add_llm_tools(*build_llm_tools(self))
        self._load_config()

    def _load_config(self) -> None:
        self.settings = load_settings(self.config)
        self.llm_tool_options = self.settings.llm_tool_options
        self._sync_llm_tools()
        logger.info(
            "im_profile 配置加载完成：llm_tool_options=%s",
            sorted(self.llm_tool_options),
        )

    def _sync_llm_tools(self) -> None:
        tool_mgr = self.context.get_llm_tool_manager()
        im_profile_tool_names = set(self.LLM_TOOL_NAME_BY_OPTION.values())
        enabled_tool_names = {
            self.LLM_TOOL_NAME_BY_OPTION[option]
            for option in self.llm_tool_options
            if option in self.LLM_TOOL_NAME_BY_OPTION
        }

        for tool in tool_mgr.func_list:
            module_path = getattr(tool, "handler_module_path", None)
            from_im_profile = module_path is None or module_path == self.__module__
            if tool.name in im_profile_tool_names and from_im_profile:
                tool.active = tool.name in enabled_tool_names

        logger.info(
            "im_profile 函数工具状态：选项=%s，启用=%s",
            sorted(self.llm_tool_options),
            sorted(enabled_tool_names),
        )

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        self._sync_llm_tools()

    @filter.on_plugin_loaded()
    async def on_plugin_loaded(self, metadata):
        if getattr(metadata, "module_path", None) == self.__module__:
            self._sync_llm_tools()

    async def _run_llm_tool(
        self,
        action: str,
        runner: Callable[[], Awaitable[ToolExecResult]],
        failure_message: str,
    ) -> ToolExecResult:
        try:
            return await runner()
        except (ValueError, RuntimeError) as exc:
            logger.warning("im_profile 函数工具 %s 参数或平台检查失败：%s", action, exc)
            return str(exc)
        except Exception:  # noqa: BLE001
            logger.exception("im_profile 函数工具 %s 执行失败", action)
            return failure_message

    async def set_profile(
        self,
        event: AstrMessageEvent,
        nickname: str,
        personal_note: str,
        sex: str,
    ) -> str:
        return await self.profile_service.set_profile(
            event=event,
            nickname=nickname,
            personal_note=personal_note,
            sex=sex,
        )

    async def set_avatar(self, event: AstrMessageEvent, avatar_url: str) -> str:
        return await self.profile_service.set_avatar(event=event, avatar_url=avatar_url)

    async def set_signature(self, event: AstrMessageEvent, signature: str) -> str:
        return await self.profile_service.set_signature(
            event=event, signature=signature
        )

    async def set_group_card(
        self,
        event: AstrMessageEvent,
        card: str,
        group_id: str | None,
    ) -> str:
        return await self.profile_service.set_group_card(
            event=event,
            card=card,
            group_id=group_id,
        )

    async def get_avatar_url(
        self,
        event: AstrMessageEvent,
        user_id: str | None,
    ) -> str:
        return await self.profile_service.get_avatar_url(event=event, user_id=user_id)

    async def get_avatar_info(
        self,
        event: AstrMessageEvent,
        user_id: str | None,
    ) -> tuple[str, str, bool]:
        return self.profile_service.resolve_avatar(event=event, user_id=user_id)
