"""
OneBot v11 消息段处理
处理各种类型的消息段
"""

from typing import Dict, Any, List, Optional, Union
from .models import MessageSegment, MessageSegmentType

class MessageSegmentBuilder:
    """消息段构建器"""
    
    @staticmethod
    def text(text: str) -> MessageSegment:
        """文本消息段"""
        return MessageSegment(
            type=MessageSegmentType.TEXT,
            data={"text": text}
        )
    
    @staticmethod
    def face(id: int) -> MessageSegment:
        """QQ表情消息段"""
        return MessageSegment(
            type=MessageSegmentType.FACE,
            data={"id": str(id)}
        )
    
    @staticmethod
    def image(file: str, type: Optional[str] = None, url: Optional[str] = None, 
              cache: bool = True, proxy: bool = True, timeout: Optional[int] = None) -> MessageSegment:
        """图片消息段"""
        data = {"file": file}
        if type is not None:
            data["type"] = type
        if url is not None:
            data["url"] = url
        if not cache:
            data["cache"] = "0"
        if not proxy:
            data["proxy"] = "0"
        if timeout is not None:
            data["timeout"] = str(timeout)
        
        return MessageSegment(
            type=MessageSegmentType.IMAGE,
            data=data
        )
    
    @staticmethod
    def record(file: str, magic: bool = False, url: Optional[str] = None,
               cache: bool = True, proxy: bool = True, timeout: Optional[int] = None) -> MessageSegment:
        """语音消息段"""
        data = {"file": file}
        if magic:
            data["magic"] = "1"
        if url is not None:
            data["url"] = url
        if not cache:
            data["cache"] = "0"
        if not proxy:
            data["proxy"] = "0"
        if timeout is not None:
            data["timeout"] = str(timeout)
        
        return MessageSegment(
            type=MessageSegmentType.RECORD,
            data=data
        )
    
    @staticmethod
    def video(file: str, url: Optional[str] = None, cache: bool = True, 
              proxy: bool = True, timeout: Optional[int] = None) -> MessageSegment:
        """短视频消息段"""
        data = {"file": file}
        if url is not None:
            data["url"] = url
        if not cache:
            data["cache"] = "0"
        if not proxy:
            data["proxy"] = "0"
        if timeout is not None:
            data["timeout"] = str(timeout)
        
        return MessageSegment(
            type=MessageSegmentType.VIDEO,
            data=data
        )
    
    @staticmethod
    def at(qq: Union[int, str]) -> MessageSegment:
        """@某人消息段"""
        return MessageSegment(
            type=MessageSegmentType.AT,
            data={"qq": str(qq)}
        )
    
    @staticmethod
    def at_all() -> MessageSegment:
        """@全体成员消息段"""
        return MessageSegment(
            type=MessageSegmentType.AT,
            data={"qq": "all"}
        )
    
    @staticmethod
    def rps() -> MessageSegment:
        """猜拳魔法表情"""
        return MessageSegment(
            type=MessageSegmentType.RPS,
            data={}
        )
    
    @staticmethod
    def dice() -> MessageSegment:
        """掷骰子魔法表情"""
        return MessageSegment(
            type=MessageSegmentType.DICE,
            data={}
        )
    
    @staticmethod
    def shake() -> MessageSegment:
        """窗口抖动"""
        return MessageSegment(
            type=MessageSegmentType.SHAKE,
            data={}
        )
    
    @staticmethod
    def poke(qq: Union[int, str]) -> MessageSegment:
        """戳一戳"""
        return MessageSegment(
            type=MessageSegmentType.POKE,
            data={"qq": str(qq)}
        )
    
    @staticmethod
    def anonymous(ignore: bool = False) -> MessageSegment:
        """匿名发消息"""
        data = {}
        if ignore:
            data["ignore"] = "1"
        
        return MessageSegment(
            type=MessageSegmentType.ANONYMOUS,
            data=data
        )
    
    @staticmethod
    def share(url: str, title: str, content: Optional[str] = None, 
              image: Optional[str] = None) -> MessageSegment:
        """链接分享"""
        data = {
            "url": url,
            "title": title
        }
        if content is not None:
            data["content"] = content
        if image is not None:
            data["image"] = image
        
        return MessageSegment(
            type=MessageSegmentType.SHARE,
            data=data
        )
    
    @staticmethod
    def contact_user(id: Union[int, str]) -> MessageSegment:
        """推荐好友"""
        return MessageSegment(
            type=MessageSegmentType.CONTACT,
            data={
                "type": "qq",
                "id": str(id)
            }
        )
    
    @staticmethod
    def contact_group(id: Union[int, str]) -> MessageSegment:
        """推荐群"""
        return MessageSegment(
            type=MessageSegmentType.CONTACT,
            data={
                "type": "group",
                "id": str(id)
            }
        )
    
    @staticmethod
    def location(lat: float, lon: float, title: Optional[str] = None, 
                 content: Optional[str] = None) -> MessageSegment:
        """位置"""
        data = {
            "lat": str(lat),
            "lon": str(lon)
        }
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        
        return MessageSegment(
            type=MessageSegmentType.LOCATION,
            data=data
        )
    
    @staticmethod
    def music(type: str, id: Union[int, str], url: Optional[str] = None,
              audio: Optional[str] = None, title: Optional[str] = None,
              content: Optional[str] = None, image: Optional[str] = None) -> MessageSegment:
        """音乐分享"""
        data = {
            "type": type,
            "id": str(id)
        }
        if url is not None:
            data["url"] = url
        if audio is not None:
            data["audio"] = audio
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if image is not None:
            data["image"] = image
        
        return MessageSegment(
            type=MessageSegmentType.MUSIC,
            data=data
        )
    
    @staticmethod
    def reply(id: Union[int, str]) -> MessageSegment:
        """回复"""
        return MessageSegment(
            type=MessageSegmentType.REPLY,
            data={"id": str(id)}
        )
    
    @staticmethod
    def forward(id: str) -> MessageSegment:
        """合并转发"""
        return MessageSegment(
            type=MessageSegmentType.FORWARD,
            data={"id": id}
        )
    
    @staticmethod
    def node_custom(user_id: Union[int, str], nickname: str, 
                    content: Union[str, List[MessageSegment]]) -> MessageSegment:
        """合并转发节点"""
        if isinstance(content, str):
            content_data = content
        else:
            content_data = [seg.dict() for seg in content]
        
        return MessageSegment(
            type=MessageSegmentType.NODE,
            data={
                "user_id": str(user_id),
                "nickname": nickname,
                "content": content_data
            }
        )
    
    @staticmethod
    def node_id(id: Union[int, str]) -> MessageSegment:
        """合并转发节点（引用消息ID）"""
        return MessageSegment(
            type=MessageSegmentType.NODE,
            data={"id": str(id)}
        )
    
    @staticmethod
    def xml(data: str) -> MessageSegment:
        """XML消息"""
        return MessageSegment(
            type=MessageSegmentType.XML,
            data={"data": data}
        )
    
    @staticmethod
    def json(data: str) -> MessageSegment:
        """JSON消息"""
        return MessageSegment(
            type=MessageSegmentType.JSON,
            data={"data": data}
        )

class MessageSegmentParser:
    """消息段解析器"""
    
    @staticmethod
    def extract_text(segments: List[MessageSegment]) -> str:
        """提取消息中的纯文本内容"""
        text_parts = []
        for segment in segments:
            if segment.type == MessageSegmentType.TEXT:
                text_parts.append(segment.data.get("text", ""))
            elif segment.type == MessageSegmentType.AT:
                qq = segment.data.get("qq", "")
                if qq == "all":
                    text_parts.append("@全体成员")
                else:
                    text_parts.append(f"@{qq}")
        return "".join(text_parts)
    
    @staticmethod
    def extract_at_list(segments: List[MessageSegment]) -> List[str]:
        """提取消息中的@列表"""
        at_list = []
        for segment in segments:
            if segment.type == MessageSegmentType.AT:
                qq = segment.data.get("qq", "")
                if qq != "all":
                    at_list.append(qq)
        return at_list
    
    @staticmethod
    def has_at_all(segments: List[MessageSegment]) -> bool:
        """检查是否包含@全体成员"""
        for segment in segments:
            if segment.type == MessageSegmentType.AT:
                if segment.data.get("qq") == "all":
                    return True
        return False
    
    @staticmethod
    def extract_images(segments: List[MessageSegment]) -> List[Dict[str, Any]]:
        """提取消息中的图片信息"""
        images = []
        for segment in segments:
            if segment.type == MessageSegmentType.IMAGE:
                images.append(segment.data)
        return images
    
    @staticmethod
    def extract_reply_id(segments: List[MessageSegment]) -> Optional[str]:
        """提取回复的消息ID"""
        for segment in segments:
            if segment.type == MessageSegmentType.REPLY:
                return segment.data.get("id")
        return None
    
    @staticmethod
    def is_command(segments: List[MessageSegment], prefix: str) -> bool:
        """检查消息是否为指令"""
        text = MessageSegmentParser.extract_text(segments).strip()
        return text.startswith(prefix)
    
    @staticmethod
    def parse_command(segments: List[MessageSegment], prefix: str) -> Optional[tuple]:
        """解析指令，返回(指令名, 参数列表)"""
        text = MessageSegmentParser.extract_text(segments).strip()
        if not text.startswith(prefix):
            return None
        
        command_text = text[len(prefix):].strip()
        if not command_text:
            return None
        
        parts = command_text.split()
        command_name = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        return command_name, args
