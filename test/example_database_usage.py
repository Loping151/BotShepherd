#!/usr/bin/env python3
"""
数据库使用示例
演示如何使用新的数据库接口进行消息查询
"""

import asyncio
from datetime import datetime, timedelta
from app.database.database_manager import DatabaseManager, MessageRecord
from app.config.config_manager import ConfigManager

async def main():
    """主函数"""
    # 初始化配置管理器和数据库管理器
    config_manager = ConfigManager()
    await config_manager.initialize()
    
    db_manager = DatabaseManager(config_manager)
    await db_manager.initialize()
    
    print("=== BotShepherd 数据库查询示例 ===\n")
    
    # 示例1: 按self_id查询消息
    print("1. 按self_id查询消息:")
    messages = await db_manager.query_messages_by_self_id("123456", limit=5)
    print(f"找到 {len(messages)} 条消息")
    for msg in messages[:3]:  # 只显示前3条
        print(f"  - [{msg.timestamp}] {msg.self_id}: {msg.message_content[:50]}...")
    print()
    
    # 示例2: 按时间段查询消息
    print("2. 按时间段查询消息 (最近24小时):")
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    messages = await db_manager.query_messages_by_time_range(start_time, end_time, limit=5)
    print(f"找到 {len(messages)} 条消息")
    for msg in messages[:3]:
        print(f"  - [{msg.timestamp}] {msg.user_id}: {msg.message_content[:50]}...")
    print()
    
    # 示例3: 按用户ID查询消息
    print("3. 按用户ID查询消息:")
    messages = await db_manager.query_messages_by_user_id("789012", limit=5)
    print(f"找到 {len(messages)} 条消息")
    for msg in messages[:3]:
        print(f"  - [{msg.timestamp}] {msg.message_content[:50]}...")
    print()
    
    # 示例4: 按群聊ID查询消息
    print("4. 按群聊ID查询消息:")
    messages = await db_manager.query_messages_by_group_id("987654", limit=5)
    print(f"找到 {len(messages)} 条消息")
    for msg in messages[:3]:
        print(f"  - [{msg.timestamp}] {msg.user_id}: {msg.message_content[:50]}...")
    print()
    
    # 示例5: 关键字搜索
    print("5. 关键字搜索 (搜索包含'测试'的消息):")
    messages = await db_manager.query_messages_by_keyword("测试", limit=5)
    print(f"找到 {len(messages)} 条消息")
    for msg in messages[:3]:
        print(f"  - [{msg.timestamp}] {msg.user_id}: {msg.message_content[:50]}...")
    print()
    
    # 示例6: 开头词搜索
    print("6. 开头词搜索 (搜索以'bs'开头的消息):")
    messages = await db_manager.query_messages_by_startswith("bs", limit=5)
    print(f"找到 {len(messages)} 条消息")
    for msg in messages[:3]:
        print(f"  - [{msg.timestamp}] {msg.user_id}: {msg.message_content[:50]}...")
    print()
    
    # 示例7: 组合查询
    print("7. 组合查询 (特定用户在特定群聊中包含关键字的消息):")
    messages = await db_manager.query_messages_combined(
        user_id="789012",
        group_id="987654", 
        keyword="hello",
        limit=5
    )
    print(f"找到 {len(messages)} 条消息")
    for msg in messages[:3]:
        print(f"  - [{msg.timestamp}] {msg.message_content[:50]}...")
    print()
    
    # 示例8: 统计消息数量
    print("8. 统计消息数量:")
    total_count = await db_manager.count_messages()
    print(f"数据库中总共有 {total_count} 条消息")
    
    # 按条件统计
    keyword_count = await db_manager.count_messages(keyword="测试")
    print(f"包含'测试'关键字的消息有 {keyword_count} 条")
    
    prefix_count = await db_manager.count_messages(prefix="bs")
    print(f"以'bs'开头的消息有 {prefix_count} 条")
    print()
    
    # 示例9: 展示MessageRecord的使用
    print("9. MessageRecord详细信息:")
    messages = await db_manager.query_messages_by_self_id("123456", limit=1)
    if messages:
        msg = messages[0]
        print(f"消息ID: {msg.id}")
        print(f"OneBot消息ID: {msg.message_id}")
        print(f"机器人ID: {msg.self_id}")
        print(f"用户ID: {msg.user_id}")
        print(f"群聊ID: {msg.group_id}")
        print(f"消息类型: {msg.message_type}")
        print(f"子类型: {msg.sub_type}")
        print(f"原始消息: {msg.raw_message}")
        print(f"消息内容: {msg.message_content}")
        print(f"发送者信息: {msg.sender_info}")
        print(f"时间戳: {msg.timestamp}")
        print(f"方向: {msg.direction}")
        print(f"连接ID: {msg.connection_id}")
        print(f"已处理: {msg.processed}")
        print(f"创建时间: {msg.created_at}")
    else:
        print("没有找到消息记录")
    
    # 关闭数据库连接
    await db_manager.close()
    print("\n=== 示例完成 ===")

if __name__ == "__main__":
    asyncio.run(main())
