import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from app.onebotv11.models import MessageSegment

logger = logging.getLogger("BotShepherd.Message")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_JSON_PATH = os.path.join(BASE_DIR, "rules.json")

if not os.path.exists(RULES_JSON_PATH):
    # 默认创建一个禁用状态且无规则的配置
    with open(RULES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"enabled": False}, f, ensure_ascii=False, indent=2)
    logger.info("[bs_plugin_message_filter] 规则文件已创建: %s", RULES_JSON_PATH)


def _load_raw_config() -> Dict[str, Any]:
    """加载原始配置（包含 enabled 等开关和规则内容）"""
    try:
        with open(RULES_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        logger.error("[bs_plugin_message_filter] 加载规则配置失败: %s", e)
        return {}


def is_rules_enabled() -> bool:
    """
    是否启用本插件的所有规则。

    - rules.json 中存在 "enabled": false 时，表示全局禁用该插件
    - 未配置或解析失败时，默认为禁言用（False）
    """
    cfg = _load_raw_config()
    enabled = cfg.get("enabled", True)
    return bool(enabled)


def _load_rules() -> Dict[str, List[Dict[str, Any]]]:
    """加载规则内容部分（仅返回各 seg_type 对应的规则列表）"""
    cfg = _load_raw_config()
    return {str(k): v for k, v in cfg.items() if isinstance(v, list)}


def _save_rules(rules: Dict[str, List[Dict[str, Any]]]) -> None:
    """保存规则文件"""
    try:
        with open(RULES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        logger.info("[bs_plugin_message_filter] 规则已保存")
    except Exception as e:
        logger.error(f"[bs_plugin_message_filter] 保存规则失败: {e}")


def apply_rule(
    seg: Union[Dict[str, Any], MessageSegment], rule: Dict[str, Any]
) -> Optional[Union[MessageSegment, Dict[str, Any]]]:
    """根据规则处理单条消息段"""
    if isinstance(seg, MessageSegment):
        seg_type = seg.type
        data = dict(seg.data)
    elif isinstance(seg, dict):
        seg_type = seg.get("type")
        data = dict(seg.get("data") or {})
    else:
        return seg

    mode = rule.get("mode")
    args = rule.get("args")

    if seg_type == "text":
        text = str(data.get("text", ""))
        if mode == "replace" and args:
            for pair in args:
                if isinstance(pair, (list, tuple)) and len(pair) == 2:
                    text = text.replace(str(pair[0]), str(pair[1]))
        elif mode == "prepend" and args is not None:
            text = f"{args}{text}"
        elif mode == "append" and args is not None:
            text = f"{text}{args}"
        data["text"] = text

    elif seg_type == "image":
        if mode == "remove":
            return None
        elif mode == "replace_file" and args:
            data["file"] = args
        elif mode == "set_summary":
            data["summary"] = str(args) if args else ""
        elif mode == "append_summary":
            data["summary"] = str(data.get("summary", "")) + (str(args) if args else "")

    if isinstance(seg, MessageSegment):
        seg.data = data
        return seg
    return {"type": seg_type, "data": data}


def apply_rules_to_message(
    segments: List[Union[Dict[str, Any], MessageSegment]],
    *,
    self_id: Optional[str] = None,
    user_id: Optional[str] = None,
    is_bot_message: Optional[bool] = None,
    debug: bool = False,
) -> List[Union[MessageSegment, Dict[str, Any]]]:
    """应用规则到消息段列表

    - 默认只处理机器人自身发送的消息：
      - 若显式传入 is_bot_message，则直接使用
      - 否则在同时提供 self_id 和 user_id 时，根据 self_id == user_id 判断
      - 两者都无法提供时，安全起见默认不处理（返回原始 segments）
    """
    if is_bot_message is None:
        if self_id is not None and user_id is not None:
            is_bot_message = str(self_id) == str(user_id)
        else:
            # 无法判断时，默认认为不是机器人消息，避免误改内容
            is_bot_message = False

    # 全局开关关闭，或不是机器人自身发送的消息，都直接返回原始消息段
    if not is_bot_message or not is_rules_enabled():
        return segments

    rules = _load_rules()
    if debug:
        logger.debug(f"[bs_plugin_message_filter] 加载规则: {rules}")

    new_segments: List[Union[MessageSegment, Dict[str, Any]]] = []

    for seg in segments:
        seg_type = seg.type if isinstance(seg, MessageSegment) else seg.get("type")
        seg_obj = seg

        if isinstance(seg_type, str) and seg_type in rules:
            for rule in rules[seg_type]:
                seg_obj = apply_rule(seg_obj, rule)
                if debug:
                    logger.debug(f"[bs_plugin_message_filter] 应用规则到 {seg_type}")
                if seg_obj is None:
                    if debug:
                        logger.debug(f"[bs_plugin_message_filter] 消息段被移除")
                    break

        if seg_obj is not None:
            new_segments.append(seg_obj)

    return new_segments


class MessageSegmentRulesPlugin:
    """消息段规则处理插件"""

    def __init__(self, debug: bool = False):
        self.name = "bs_plugin_message_filter"
        self.version = "1.0.0"
        self.debug = debug
        logger.info(f"[{self.name}] 插件初始化")

    def filter_send_message(
        self, event_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """拦截发送消息并应用规则"""
        try:
            action = event_data.get("action")
            if action not in ["send_msg", "send_private_msg", "send_group_msg"]:
                return event_data

            params = event_data.get("params", {})
            message = params.get("message")

            if not message:
                return event_data

            # 标准化消息格式
            if isinstance(message, str):
                segments = [{"type": "text", "data": {"text": message}}]
            elif isinstance(message, list):
                segments = message
            else:
                return event_data

            # 应用规则
            new_segments = apply_rules_to_message(
                segments,
                self_id=event_data.get("self_id"),
                is_bot_message=True,
                debug=self.debug,
            )

            params["message"] = new_segments
            event_data["params"] = params

            if self.debug:
                logger.debug(f"[{self.name}] 原始: {segments}")
                logger.debug(f"[{self.name}] 处理后: {new_segments}")

            return event_data

        except Exception as e:
            logger.error(f"[{self.name}] 错误: {e}", exc_info=True)
            return event_data

    def register(self, processor):
        """注册过滤器"""
        from app.server.message_processor import MessageProcessor

        if not isinstance(processor, MessageProcessor):
            logger.error(f"[{self.name}] processor 类型错误")
            return

        processor.register_filter(
            filter_func=self.filter_send_message, direction="send", priority=45
        )
        logger.info(f"[{self.name}] 已注册")


def setup(processor):
    """插件入口"""
    plugin = MessageSegmentRulesPlugin(debug=False)
    plugin.register(processor)
    return plugin


__all__ = [
    "setup",
    "apply_rules_to_message",
    "apply_rule",
    "_load_rules",
    "_save_rules",
    "RULES_JSON_PATH",
    "is_rules_enabled",
]
