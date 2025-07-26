import os
import sys
import asyncio

from app.onebotv11.models import ApiRequest
from ..onebotv11.api_handler import ApiHandler

REBOOT_RECORD = "data/.reboot"

def is_rebooting():
    """检查是否正在重启"""
    return os.path.exists(REBOOT_RECORD)

async def reboot(event = None, wait_seconds: int = 3):
    """重启程序"""
    if event:
        try:
            self_id = event.self_id
            user_id = event.user_id
            group_id = event.group_id if hasattr(event, "group_id") else None
            if not is_rebooting():
                with open(REBOOT_RECORD, "w", encoding="utf-8") as f:
                    f.write(f"{self_id}\n{user_id}\n{group_id}")
        except Exception as e:
            print(f"记录重启数据失败: {e}")
    
    await asyncio.sleep(wait_seconds)
    os.execv(sys.executable, ['python'] + sys.argv)


async def read_reboot_record():
    """读取重启记录"""
    if not os.path.exists(REBOOT_RECORD):
        return None
    try:
        with open(REBOOT_RECORD, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) != 3:
                return None
            return {
                "self_id": lines[0].strip(),
                "user_id": lines[1].strip(),
                "group_id": lines[2].strip() if lines[2].strip() != "None" else None
            }
    except Exception as e:
        print(f"读取重启数据失败: {e}")
        return None


async def construct_reboot_message(self_id: str) -> dict | None:
    """构造重启消息"""
    reboot_data = await read_reboot_record()
    if not reboot_data:
        return None
    if reboot_data["self_id"] != self_id:
        return None
    os.remove(REBOOT_RECORD)
    return ApiHandler.create_send_msg_request(
        message_type="group" if reboot_data["group_id"] else "private",
        user_id=reboot_data["user_id"],
        group_id=reboot_data["group_id"],
        message="BotShepherd重启成功！"
    ).model_dump()
