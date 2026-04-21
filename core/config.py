from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from astrbot.api import logger

LLM_TOOL_OPTIONS = (
    "profile",
    "avatar",
    "group_card",
    "avatar_lookup",
)

LEGACY_LLM_TOOL_OPTION_ALIASES = {
    "signature": "profile",
}


def _normalize_str_set(values: list[Any]) -> set[str]:
    return {str(item).strip().lower() for item in values if str(item).strip()}


def _apply_legacy_option_aliases(options: set[str]) -> set[str]:
    migrated: set[str] = set()
    replaced: dict[str, str] = {}
    for option in options:
        mapped = LEGACY_LLM_TOOL_OPTION_ALIASES.get(option, option)
        migrated.add(mapped)
        if mapped != option:
            replaced[option] = mapped

    if replaced:
        logger.info(
            "im_profile llm_tool_options 已迁移历史选项：%s",
            ", ".join(f"{k}->{v}" for k, v in sorted(replaced.items())),
        )
    return migrated


@dataclass(slots=True)
class IMProfileSettings:
    llm_tool_options: set[str]


def load_settings(config: Mapping[str, Any] | None) -> IMProfileSettings:
    default_options = set(LLM_TOOL_OPTIONS)

    if not config:
        logger.warning("im_profile 未载入专用配置，将使用默认值。")
        return IMProfileSettings(llm_tool_options=default_options)

    llm_tool_options_raw = config.get("llm_tool_options", None)
    llm_tool_options: set[str]

    if llm_tool_options_raw is None:
        if "enable_llm_tools" in config:
            llm_tool_options = (
                default_options
                if bool(config.get("enable_llm_tools", False))
                else set()
            )
        else:
            llm_tool_options = default_options
    elif isinstance(llm_tool_options_raw, list):
        llm_tool_options = _normalize_str_set(llm_tool_options_raw)
    else:
        logger.warning(
            "im_profile llm_tool_options 配置应为列表，实际收到 %r，使用默认值。",
            llm_tool_options_raw,
        )
        llm_tool_options = default_options

    llm_tool_options = _apply_legacy_option_aliases(llm_tool_options)

    unsupported_options = llm_tool_options - set(LLM_TOOL_OPTIONS)
    if unsupported_options:
        logger.warning(
            "im_profile llm_tool_options 包含不支持项：%s，已忽略。",
            sorted(unsupported_options),
        )
        llm_tool_options = llm_tool_options.intersection(set(LLM_TOOL_OPTIONS))

    return IMProfileSettings(llm_tool_options=llm_tool_options)
