import asyncio
import websockets
import json
from datetime import datetime

# --- 配置区 ---
# 代理服务器监听的地址和端口 (给 Yunzai 连接)
PROXY_HOST = "localhost"
PROXY_PORT = 2537

# 目标服务器的地址和端口 (NapCat 的实际地址)
TARGET_URI = "ws://localhost:2536/OneBotv11" 

# 是否将日志保存到文件
LOG_TO_FILE = True
LOG_FILE_NAME = "ws_log.txt"
# --- 配置区结束 ---

# 用于美化输出的日志函数
def log_message(direction, message):
    """记录并打印消息"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    log_content = f"[{timestamp}] [{direction}]\n"
    
    # 尝试将消息格式化为 JSON 以便阅读
    try:
        data = json.loads(message)
        log_content += json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        # 如果不是有效的 JSON，则直接输出原始消息
        log_content += message
        
    print(log_content + "\n" + "="*50 + "\n")
    
    if LOG_TO_FILE:
        try:
            with open(LOG_FILE_NAME, 'a', encoding='utf-8') as f:
                f.write(log_content + "\n" + "="*50 + "\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")


# <-- CHANGE #1: Removed the 'path' argument from the function definition
async def proxy_handler(client_ws):
    """
    处理客户端连接，并建立到目标服务器的连接，然后在两者之间转发消息。
    `client_ws` 是来自 Yunzai 的连接。
    """
    client_ip = client_ws.remote_address
    print(f"[*] New connection from Yunzai: {client_ip}")
    
    # 尝试连接到目标服务器 (NapCat)
    try:
        # <-- CHANGE #2: Directly use the globally defined TARGET_URI
        async with websockets.connect(TARGET_URI) as target_ws:
            print(f"[*] Successfully connected to NapCat: {TARGET_URI}")
            
            # 创建两个任务，一个用于从 Yunzai -> NapCat，另一个用于 NapCat -> Yunzai
            task_client_to_target = asyncio.create_task(forward(client_ws, target_ws, "NapCat -> Yunzai"))
            task_target_to_client = asyncio.create_task(forward(target_ws, client_ws, "Yunzai -> NapCat"))
            
            # 等待任一任务完成 (通常是因为一方断开连接)
            done, pending = await asyncio.wait(
                [task_client_to_target, task_target_to_client],
                return_when=asyncio.FIRST_COMPLETED,
            )
            
            # 取消仍在运行的任务
            for task in pending:
                task.cancel()

    except Exception as e:
        print(f"[!] Error connecting to NapCat: {e}")
    finally:
        print(f"[*] Connection closed for {client_ip}")


async def forward(source_ws, dest_ws, direction):
    """从源 websocket 接收消息并转发到目标 websocket"""
    async for message in source_ws:
        log_message(direction, message)
        await dest_ws.send(message)


async def main():
    # 启动代理服务器
    async with websockets.serve(proxy_handler, PROXY_HOST, PROXY_PORT):
        print(f"[*] WebSocket proxy is running on ws://{PROXY_HOST}:{PROXY_PORT}")
        print("[*] Waiting for Yunzai connection...")
        # 让服务器一直运行
        await asyncio.Future()

if __name__ == "__main__":
    if LOG_TO_FILE:
        print(f"[*] Logging to file: {LOG_FILE_NAME}")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Proxy server is shutting down.")