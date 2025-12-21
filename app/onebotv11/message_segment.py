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

    @staticmethod
    def file(file: str, name: Optional[str] = None, url: Optional[str] = None) -> MessageSegment:
        """文件消息段

        Args:
            file: 文件路径或base64编码的文件内容（格式：base64://...）
            name: 文件名
            url: 文件URL
        """
        data = {"file": file}
        if name is not None:
            data["name"] = name
        if url is not None:
            data["url"] = url

        return MessageSegment(
            type=MessageSegmentType.FILE,
            data=data
        )

class MessageSegmentParser:
    """消息段解析器"""
    
    @staticmethod
    def extract_text(segments: List[MessageSegment]) -> str:
        """提取消息中的纯文本内容"""
        text_parts = []
        # at_list = []
        # 暂时去掉 at
        for segment in segments:
            if segment.type == MessageSegmentType.TEXT:
                text_parts.append(segment.data.get("text", ""))
            # elif segment.type == MessageSegmentType.AT:
            #     qq = segment.data.get("qq", "")
            #     if qq == "all":
            #         at_list.append("@全体成员")
            #     else:
            #         at_list.append(f"@{qq}")
                    
        # return " ".join(text_parts + at_list)
        return " ".join(text_parts)
    
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
        
        command_text = text[len(prefix):].strip()
        if not command_text:
            return None
        
        parts = command_text.split()
        command_name = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        return command_name, args

    @staticmethod
    def message2raw_message(segments: List[MessageSegment]) -> str:
        """将消息段数组转换为CQ码格式的raw_message字符串"""
        if not segments:
            return ""

        result_parts = []

        for segment in segments:
            if isinstance(segment, str):
                result_parts.append(segment)
                continue

            if isinstance(segment, dict):
                segment = MessageSegment(**segment)

            if segment.type == MessageSegmentType.TEXT:
                # 文本消息直接添加
                text = segment.data.get("text", "")
                result_parts.append(text)

            elif segment.type == MessageSegmentType.AT:
                # @消息：[CQ:at,qq=QQ号]
                qq = segment.data.get("qq", "")
                result_parts.append(f"[CQ:at,qq={qq}]")

            elif segment.type == MessageSegmentType.FACE:
                # QQ表情：[CQ:face,id=表情ID]
                face_id = segment.data.get("id", "")
                result_parts.append(f"[CQ:face,id={face_id}]")

            elif segment.type == MessageSegmentType.IMAGE:
                # 图片：[CQ:image,file=文件名,sub_type=子类型,url=链接,file_size=文件大小]
                params = []
                for key in ["file", "sub_type", "url", "file_size", "summary"]:
                    if key in segment.data and segment.data[key] is not None:
                        value = MessageSegmentParser._escape_cq_param(str(segment.data[key]))
                        if value.startswith("base64://"):
                            value = "base64://..."
                        params.append(f"{key}={value}")
                result_parts.append("[CQ:image,{}]".format(','.join(params)))

            elif segment.type == MessageSegmentType.RECORD:
                # 语音：[CQ:record,file=文件名]
                params = []
                for key in ["file", "magic", "url", "cache", "proxy", "timeout"]:
                    if key in segment.data and segment.data[key] is not None:
                        value = MessageSegmentParser._escape_cq_param(str(segment.data[key]))
                        if value.startswith("base64://"):
                            value = "base64://..."
                        params.append(f"{key}={value}")
                result_parts.append("[CQ:record,{}]".format(','.join(params)))

            elif segment.type == MessageSegmentType.VIDEO:
                # 短视频：[CQ:video,file=文件名]
                params = []
                for key in ["file", "url", "cache", "proxy", "timeout"]:
                    if key in segment.data and segment.data[key] is not None:
                        value = MessageSegmentParser._escape_cq_param(str(segment.data[key]))
                        if value.startswith("base64://"):
                            value = "base64://..."
                        params.append(f"{key}={value}")
                result_parts.append("[CQ:video,{}]".format(','.join(params)))

            elif segment.type == MessageSegmentType.REPLY:
                # 回复：[CQ:reply,id=消息ID]
                reply_id = segment.data.get("id", "")
                result_parts.append(f"[CQ:reply,id={reply_id}]")

            elif segment.type == MessageSegmentType.JSON:
                # JSON消息：[CQ:json,data=JSON数据]
                json_data = segment.data.get("data", "")
                escaped_data = MessageSegmentParser._escape_cq_param(json_data)
                result_parts.append(f"[CQ:json,data={escaped_data}]")

            elif segment.type == MessageSegmentType.XML:
                # XML消息：[CQ:xml,data=XML数据]
                xml_data = segment.data.get("data", "")
                escaped_data = MessageSegmentParser._escape_cq_param(xml_data)
                result_parts.append(f"[CQ:xml,data={escaped_data}]")

            elif segment.type == MessageSegmentType.SHARE:
                # 链接分享：[CQ:share,url=链接,title=标题,content=内容,image=图片]
                params = []
                for key in ["url", "title", "content", "image"]:
                    if key in segment.data and segment.data[key] is not None:
                        value = MessageSegmentParser._escape_cq_param(str(segment.data[key]))
                        params.append(f"{key}={value}")
                result_parts.append("[CQ:share,{}]".format(','.join(params)))

            elif segment.type == MessageSegmentType.CONTACT:
                # 推荐好友/群：[CQ:contact,type=类型,id=ID]
                params = []
                for key in ["type", "id"]:
                    if key in segment.data and segment.data[key] is not None:
                        value = MessageSegmentParser._escape_cq_param(str(segment.data[key]))
                        params.append(f"{key}={value}")
                result_parts.append("[CQ:contact,{}]".format(','.join(params)))

            elif segment.type == MessageSegmentType.LOCATION:
                # 位置：[CQ:location,lat=纬度,lon=经度,title=标题,content=内容]
                params = []
                for key in ["lat", "lon", "title", "content"]:
                    if key in segment.data and segment.data[key] is not None:
                        value = MessageSegmentParser._escape_cq_param(str(segment.data[key]))
                        params.append(f"{key}={value}")
                result_parts.append("[CQ:location,{}]".format(','.join(params)))

            elif segment.type == MessageSegmentType.MUSIC:
                # 音乐：[CQ:music,type=类型,id=ID]
                params = []
                for key in ["type", "id", "url", "audio", "title", "content", "image"]:
                    if key in segment.data and segment.data[key] is not None:
                        value = MessageSegmentParser._escape_cq_param(str(segment.data[key]))
                        params.append(f"{key}={value}")
                result_parts.append("[CQ:music,{}]".format(','.join(params)))

            elif segment.type == MessageSegmentType.FORWARD:
                # 合并转发：[CQ:forward,id=ID]
                forward_id = segment.data.get("id", "")
                result_parts.append(f"[CQ:forward,id={forward_id}]")

            elif segment.type == MessageSegmentType.NODE:
                # 合并转发节点：[CQ:node,id=ID] 或 [CQ:node,user_id=用户ID,nickname=昵称,content=内容]
                if "id" in segment.data:
                    node_id = segment.data.get("id", "")
                    result_parts.append(f"[CQ:node,id={node_id}]")
                else:
                    params = []
                    for key in ["user_id", "nickname", "content"]:
                        if key in segment.data and segment.data[key] is not None:
                            value = MessageSegmentParser._escape_cq_param(str(segment.data[key]))
                            params.append(f"{key}={value}")
                    result_parts.append("[CQ:node,{}]".format(','.join(params)))

            elif segment.type == MessageSegmentType.RPS:
                # 猜拳魔法表情：[CQ:rps]
                result_parts.append("[CQ:rps]")

            elif segment.type == MessageSegmentType.DICE:
                # 掷骰子魔法表情：[CQ:dice]
                result_parts.append("[CQ:dice]")

            elif segment.type == MessageSegmentType.SHAKE:
                # 窗口抖动：[CQ:shake]
                result_parts.append("[CQ:shake]")

            elif segment.type == MessageSegmentType.POKE:
                # 戳一戳：[CQ:poke,qq=QQ号]
                qq = segment.data.get("qq", "")
                result_parts.append(f"[CQ:poke,qq={qq}]")

            elif segment.type == MessageSegmentType.ANONYMOUS:
                # 匿名发消息：[CQ:anonymous,ignore=是否忽略]
                if "ignore" in segment.data and segment.data["ignore"]:
                    result_parts.append("[CQ:anonymous,ignore=1]")
                else:
                    result_parts.append("[CQ:anonymous]")

            else:
                # 未知类型，尝试通用处理
                params = []
                for key, value in segment.data.items():
                    if value is not None:
                        escaped_value = MessageSegmentParser._escape_cq_param(str(value))
                        params.append(f"{key}={escaped_value}")
                if params:
                    result_parts.append("[CQ:{},{}]".format(segment.type, ','.join(params)))
                else:
                    result_parts.append(f"[CQ:{segment.type}]")

        return "".join(result_parts)

    @staticmethod
    def _escape_cq_param(text: str) -> str:
        """转义CQ码参数中的特殊字符"""
        if not text:
            return text

        # CQ码参数转义规则
        text = text.replace("&", "&amp;")  # & 必须最先转义
        text = text.replace("[", "&#91;")
        text = text.replace("]", "&#93;")
        text = text.replace(",", "&#44;")

        return text
