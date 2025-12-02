"""
消息段规则处理插件导出入口

- 主要逻辑在同目录的 `plugin.py` 中
- 导入本包时，会自动把发送消息的过滤流程挂接上规则处理
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.onebotv11.models import Event
from app.server.filter_manager import FilterManager

from .plugin import RULES_JSON_PATH, apply_rule, apply_rules_to_message, logger


async def _patched_filter_send_message(
    self: FilterManager,
    event: Event,
    message_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    包装原有的发送过滤逻辑，在其之后再套一层消息段规则处理。

    - 只对机器人发送的消息生效（通过 self_id == user_id 判断）
    - 如果原过滤器返回 None（表示拦截），则不再处理
    """
    # 保留原有 FilterManager 的发送过滤逻辑
    original = _patched_filter_send_message.__original_filter  # type: ignore[attr-defined]
    result = await original(self, event, message_data)
    if not result:
        return result

    try:
        params = result.get("params") or {}
        segments = params.get("message")
        if not isinstance(segments, list):
            return result

        new_segments = apply_rules_to_message(
            segments,
            self_id=str(getattr(event, "self_id", "")),
            user_id=str(getattr(event, "user_id", "")),
            is_bot_message=None,  # 走内部 self_id == user_id 判断
            debug=False,
        )
        params["message"] = new_segments
        result["params"] = params
        return result
    except Exception as e:  # 防御性处理，任何异常都不影响主流程
        logger.error(
            "[bs_plugin_message_filter] 发送消息规则处理失败: %s", e, exc_info=True
        )
        return result


def _monkey_patch_filter_manager() -> None:
    """在导入插件时，对 FilterManager 进行一次性打补丁。"""
    if getattr(FilterManager, "_bs_message_rules_patched", False):
        return

    # 记录原始实现到包装函数属性上，方便内部调用
    setattr(
        _patched_filter_send_message,
        "__original_filter",
        FilterManager.filter_send_message,
    )
    FilterManager.filter_send_message = _patched_filter_send_message  # type: ignore[assignment]
    setattr(FilterManager, "_bs_message_rules_patched", True)
    logger.info("[bs_plugin_message_filter] 已挂接")


# 模块导入时立即打补丁
_monkey_patch_filter_manager()


__all__ = [
    "apply_rules_to_message",
    "apply_rule",
    "RULES_JSON_PATH",
]
