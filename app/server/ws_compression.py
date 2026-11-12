"""
WebSocket 压缩策略（全自动，无配置项）

- 本机连接不协商压缩：回环上省不了带宽，只让两头各在事件循环里白压一遍。
- 其余连接照常协商，对端发来压缩过的消息照样能收；自己发出去的逐条判断：
  小消息直接压，大消息抽样试压，压不动的（图片、视频的 base64 只能压到约 76%，
  25MB 压一次约 0.6 秒）原样发。每条消息帧头有标志位表明压没压，接收端按标志处理，
  不需要对端配合。
"""

import ipaddress
import zlib
from urllib.parse import urlsplit

SMALL_MESSAGE = 16 * 1024   # 不超过这么大的直接压，不值得判断
SAMPLE_COUNT = 3            # 大消息在 1/4、2/4、3/4 处各取一段试压
SAMPLE_SIZE = 2048
SAMPLE_MAX_RATIO = 0.7      # 试压后仍超过原大小的这个比例就不压（base64 压不到 0.75 以下）


def is_local_host(host: str) -> bool:
    """是否本机地址：localhost、回环、0.0.0.0（连它实际也是连本机）"""
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return ip.is_loopback or ip.is_unspecified


def is_local_endpoint(endpoint: str) -> bool:
    return is_local_host(urlsplit(endpoint).hostname or "")


def worth_compressing(data) -> bool:
    """这条消息值不值得压"""
    size = len(data)
    if size <= SMALL_MESSAGE:
        return True
    step = size // (SAMPLE_COUNT + 1)
    sample = b"".join(
        bytes(data[i * step:i * step + SAMPLE_SIZE]) for i in range(1, SAMPLE_COUNT + 1)
    )
    return len(zlib.compress(sample, 1)) < len(sample) * SAMPLE_MAX_RATIO


try:
    from websockets import frames
    from websockets.extensions.permessage_deflate import (
        ClientPerMessageDeflateFactory,
        PerMessageDeflate,
        ServerPerMessageDeflateFactory,
    )

    class SelectivePerMessageDeflate(PerMessageDeflate):
        """库自带的实现协商成功后每条都压，这里改成只压值得压的。

        不压的消息不带压缩标志、也不经过压缩器，两端的压缩上下文不受影响。
        """

        _skip_message = False

        def encode(self, frame):
            if frame.opcode in frames.CTRL_OPCODES:
                return frame
            if frame.opcode is not frames.OP_CONT:
                # 分片消息以首帧为准，后续分片跟随
                self._skip_message = not worth_compressing(frame.data)
            if self._skip_message:
                return frame
            return super().encode(frame)

    class _ClientFactory(ClientPerMessageDeflateFactory):
        def process_response_params(self, params, accepted_extensions):
            extension = super().process_response_params(params, accepted_extensions)
            extension.__class__ = SelectivePerMessageDeflate
            return extension

    class _ServerFactory(ServerPerMessageDeflateFactory):
        def process_request_params(self, params, accepted_extensions):
            response_params, extension = super().process_request_params(params, accepted_extensions)
            extension.__class__ = SelectivePerMessageDeflate
            return response_params, extension

    # 参数与库里 compression="deflate" 的默认值一致
    def client_compression() -> dict:
        """websockets.connect 的压缩参数"""
        return {
            "compression": None,
            "extensions": [_ClientFactory(compress_settings={"memLevel": 5})],
        }

    def server_compression() -> dict:
        """websockets.serve 的压缩参数"""
        return {
            "compression": None,
            "extensions": [_ServerFactory(
                server_max_window_bits=12,
                client_max_window_bits=12,
                compress_settings={"memLevel": 5},
            )],
        }

except Exception:  # websockets 内部结构变了：退回库自带的每条都压
    def client_compression() -> dict:
        return {"compression": "deflate"}

    def server_compression() -> dict:
        return {"compression": "deflate"}
