"""
Web服务器
提供Web管理界面的后端API
"""

import asyncio
import re
import time
import concurrent.futures
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import requests
from waitress import serve
import threading

from app.utils.reboot import reboot

class WebServer:
    """Web服务器"""
    
    def __init__(self, config_manager, database_manager, proxy_server, logger, port=5100, loop=None):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.proxy_server = proxy_server
        self.logger = logger
        self.port = port
        self.loop = loop
        
        # 创建Flask应用
        self.app = Flask(__name__, 
                        template_folder="../../templates",
                        static_folder="../../static")
        self.app.secret_key = "botshepherd_secret_key_change_me"
        
        # 启用CORS
        CORS(self.app)
        
        # 注册路由
        self._register_routes()
        
        self.server_thread = None
        self.running = False
    
    def _register_routes(self):
        """注册路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('index.html')
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """登录页面"""
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                # 验证登录
                global_config = self.config_manager.get_global_config()
                web_auth = global_config.get('web_auth', {})
                
                if (username == web_auth.get('username', 'admin') and 
                    password == web_auth.get('password', 'admin')):
                    session['authenticated'] = True
                    return redirect(url_for('index'))
                else:
                    return render_template('login.html', error='用户名或密码错误')
            
            return render_template('login.html')
        
        @self.app.route('/logout')
        def logout():
            """登出"""
            session.pop('authenticated', None)
            return redirect(url_for('login'))

        # 页面路由
        @self.app.route('/connections')
        def connections():
            """连接管理页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('connections.html')

        @self.app.route('/accounts')
        def accounts():
            """账号管理页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('accounts.html')

        @self.app.route('/groups')
        def groups():
            """群组管理页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('groups.html')

        @self.app.route('/statistics')
        def statistics():
            """统计分析页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('statistics.html')

        @self.app.route('/query')
        def query():
            """消息查询页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('query.html')

        @self.app.route('/filters')
        def filters():
            """过滤设置页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('filters.html')

        @self.app.route('/logs')
        def logs():
            """日志查看页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('logs.html')

        @self.app.route('/settings')
        def settings():
            """系统设置页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('settings.html')

        @self.app.route('/backups')
        def backups():
            """备份管理页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('backups.html')

        # API路由
        @self.app.route('/api/version')
        def api_version():
            """版本信息API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                from app import __version__, __author__, __description__
                return jsonify({
                    'version': __version__,
                    'author': __author__,
                    'description': __description__
                })
            except Exception as e:
                return jsonify({
                    'version': 'unknown',
                    'author': 'unknown',
                    'description': 'unknown'
                })
                
                
        @self.app.route('/api/github-version')
        def api_remote_version():
            """从 GitHub 获取版本信息 API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 获取代理配置
                global_config = self.config_manager.get_global_config()
                proxy = global_config.get("proxy", "")
                proxies = {"http": proxy, "https": proxy} if proxy else None

                response = requests.get(
                    "https://raw.githubusercontent.com/Loping151/BotShepherd/main/app/__init__.py",
                    timeout=5,
                    proxies=proxies
                )
                response.raise_for_status()
                content = response.text

                # 提取 __version__、__author__、__description__
                version = re.search(r"__version__\s*=\s*['\"](.+?)['\"]", content)
                author = re.search(r"__author__\s*=\s*['\"](.+?)['\"]", content)
                description = re.search(r"__description__\s*=\s*['\"](.+?)['\"]", content)

                remote_version = version.group(1) if version else None
                from app import __version__, __author__, __description__

                # 检查是否需要更新
                needs_update = False
                if remote_version and remote_version != __version__:
                    needs_update = True

                return jsonify({
                    'version': remote_version if remote_version else '获取失败',
                    'author': author.group(1) if author else 'unknown',
                    'description': description.group(1) if description else 'unknown',
                    'local_version': __version__,
                    'needs_update': needs_update
                })
            except Exception as e:
                return jsonify({
                    'version': '访问Github失败',
                    'author': 'unknown',
                    'description': 'unknown',
                    'needs_update': False,
                    'error': str(e)
                })

        @self.app.route('/api/update', methods=['POST'])
        def api_update():
            """执行系统更新（git pull）"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                import subprocess
                import os

                # 获取项目根目录
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

                # 执行 git pull
                result = subprocess.run(
                    ['git', 'pull'],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return jsonify({
                        'success': True,
                        'message': '更新成功，请重启系统以应用更新',
                        'output': result.stdout
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': '更新失败',
                        'error': result.stderr
                    }), 500

            except subprocess.TimeoutExpired:
                return jsonify({
                    'success': False,
                    'message': '更新超时'
                }), 500
            except FileNotFoundError:
                return jsonify({
                    'success': False,
                    'message': 'Git未安装或不在PATH中'
                }), 500
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'更新失败: {str(e)}'
                }), 500

        @self.app.route('/api/status')
        def api_status():
            """系统状态API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            return jsonify({
                'status': 'running',
                'active_connections': len(self.proxy_server.active_connections),
                'timestamp': time.time()
            })

        @self.app.route('/api/dashboard-content')
        def api_dashboard_content():
            """获取仪表盘markdown内容"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                from pathlib import Path
                markdown_file = Path("templates/dashboard.md")
                if markdown_file.exists():
                    with open(markdown_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return jsonify({'content': content})
                else:
                    return jsonify({'content': '# 欢迎使用 BotShepherd\n\n仪表盘内容文件未找到。'})
            except Exception as e:
                self.logger.web.error(f"读取仪表盘内容失败: {e}")
                return jsonify({'error': f'读取内容失败: {str(e)}'}), 500

        @self.app.route('/api/system-resources')
        def api_system_resources():
            """获取系统资源信息"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                import psutil
                import platform
                import time
                from datetime import datetime, timedelta

                # 获取当前进程和系统资源占用
                process = psutil.Process()
                app_cpu = process.cpu_percent(interval=1)
                total_cpu = psutil.cpu_percent(interval=1)
                app_mem = process.memory_info().rss / (1024 * 1024)  # MB

                # 获取内存信息
                memory = psutil.virtual_memory()
                total_mem_gb = memory.total / (1024 * 1024 * 1024)  # GB
                used_mem_gb = memory.used / (1024 * 1024 * 1024)  # GB
                available_mem_gb = memory.available / (1024 * 1024 * 1024)  # GB

                # 获取磁盘信息
                disk = psutil.disk_usage('/')
                disk_total_gb = disk.total / (1024 * 1024 * 1024)  # GB
                disk_used_gb = disk.used / (1024 * 1024 * 1024)  # GB
                disk_free_gb = disk.free / (1024 * 1024 * 1024)  # GB
                disk_percent = (disk.used / disk.total) * 100

                # 获取系统信息
                cpu_cores = psutil.cpu_count()
                cpu_freq = psutil.cpu_freq()
                system_info = f"{platform.system()} {platform.release()}"
                python_version = platform.python_version()

                # 获取系统启动时间
                boot_time = psutil.boot_time()
                system_uptime_seconds = time.time() - boot_time
                system_uptime_hours = int(system_uptime_seconds / 3600)
                system_uptime_days = system_uptime_hours // 24
                system_uptime_hours_remainder = system_uptime_hours % 24

                # 计算应用运行时间（从进程创建时间开始）
                process_start_time = process.create_time()
                app_uptime_seconds = time.time() - process_start_time
                app_uptime_minutes = int(app_uptime_seconds / 60)
                app_uptime_hours = app_uptime_minutes // 60
                app_uptime_minutes_remainder = app_uptime_minutes % 60

                return jsonify({
                    'app_cpu': round(app_cpu, 1),
                    'total_cpu': round(total_cpu, 1),
                    'app_memory': round(app_mem, 1),
                    'total_memory_gb': round(total_mem_gb, 2),
                    'used_memory_gb': round(used_mem_gb, 2),
                    'available_memory_gb': round(available_mem_gb, 2),
                    'memory_percent': round(memory.percent, 1),
                    'disk_total_gb': round(disk_total_gb, 2),
                    'disk_used_gb': round(disk_used_gb, 2),
                    'disk_free_gb': round(disk_free_gb, 2),
                    'disk_percent': round(disk_percent, 1),
                    'cpu_cores': cpu_cores,
                    'cpu_freq_current': round(cpu_freq.current, 0) if cpu_freq else 0,
                    'cpu_freq_max': round(cpu_freq.max, 0) if cpu_freq else 0,
                    'system_info': system_info,
                    'python_version': python_version,
                    'system_uptime_days': system_uptime_days,
                    'system_uptime_hours': system_uptime_hours_remainder,
                    'app_uptime_hours': app_uptime_hours,
                    'app_uptime_minutes': app_uptime_minutes_remainder
                })
            except Exception as e:
                self.logger.web.error(f"获取系统资源信息失败: {e}")
                return jsonify({'error': f'获取系统资源信息失败: {str(e)}'}), 500

        @self.app.route('/api/database-status')
        def api_database_status():
            """获取数据库状态信息"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 获取数据库大小（MB）
                db_size_bytes = self.database_manager.get_database_size()
                db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

                # 获取消息记录数量
                message_count = asyncio.run(self.database_manager.get_total_message_count())

                # 获取数据保留天数
                global_config = self.config_manager.get_global_config()
                db_config = global_config.get("database", {})
                retention_days = db_config.get('auto_expire_days', 30)

                # 获取存储路径
                storage_path = str(self.database_manager.db_path.parent) if self.database_manager.db_path else "./data"

                return jsonify({
                    'db_size_mb': db_size_mb,
                    'message_count': message_count,
                    'retention_days': retention_days,
                    'storage_path': storage_path
                })
            except Exception as e:
                self.logger.web.error(f"获取数据库状态失败: {e}")
                return jsonify({'error': f'获取数据库状态失败: {str(e)}'}), 500

        @self.app.route('/api/connections')
        def api_connections():
            """连接配置API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 重新加载连接配置以获取最新数据
                asyncio.run(self.config_manager._load_connections_config())
                connections = self.config_manager.get_connections_config()

                # 获取连接状态
                connection_statuses = {}
                if hasattr(self, 'proxy_server') and self.proxy_server:
                    connection_statuses = self.proxy_server.get_connection_statuses()

                # 将状态信息合并到连接配置中
                for connection_id, status in connection_statuses.items():
                    if connection_id in connections:
                        connections[connection_id]['status'] = status

                return jsonify(connections)
            except Exception as e:
                self.logger.web.error(f"获取连接配置失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/connections/<connection_id>', methods=['PUT'])
        def api_update_connection(connection_id):
            """更新连接配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                config = request.get_json()

                # 获取原配置以比较
                old_config = self.config_manager.get_connection_config(connection_id)
                old_enabled = old_config.get('enabled', False) if old_config else False
                old_targets = old_config.get('target_endpoints', []) if old_config else []
                new_enabled = config.get('enabled', False)
                new_targets = config.get('target_endpoints', [])

                # 保存配置
                asyncio.run(
                    self.config_manager.save_connection_config(connection_id, config)
                )

                # 判断是否需要重启连接
                # 1. enabled状态发生变化
                # 2. 目标端点发生变化
                # 3. 客户端端点发生变化（需要重启监听）
                old_client_endpoint = old_config.get('client_endpoint', '') if old_config else ''
                new_client_endpoint = config.get('client_endpoint', '')

                needs_restart = (
                    old_enabled != new_enabled or
                    old_targets != new_targets or
                    old_client_endpoint != new_client_endpoint
                )

                if needs_restart and hasattr(self, 'proxy_server') and self.proxy_server:
                    self.logger.web.info(f"连接 {connection_id} 配置已更改，正在重启连接代理...")

                    # 使用事件循环重启连接
                    if self.loop:
                        self.loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(
                                self.proxy_server.restart_connection(connection_id)
                            )
                        )
                    else:
                        asyncio.run(self.proxy_server.restart_connection(connection_id))

                return jsonify({'success': True})
            except ValueError as e:
                # 配置验证错误，返回400状态码和具体错误信息
                self.logger.web.warning(f"连接配置验证失败: {e}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.web.error(f"更新连接配置失败: {e}")
                return jsonify({'error': f'更新连接配置失败: {str(e)}'}), 500
        
        @self.app.route('/api/global-config')
        def api_global_config():
            """全局配置API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                config = self.config_manager.get_global_config()
                return jsonify(config)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/global-config', methods=['PUT'])
        def api_update_global_config():
            """更新全局配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                updates = request.get_json()
                asyncio.run(
                    self.config_manager.update_global_config(updates)
                )
                return jsonify({'success': True})
            except ValueError as e:
                self.logger.web.warning(f"全局配置验证失败: {e}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.web.error(f"更新全局配置失败: {e}")
                return jsonify({'error': f'更新全局配置失败: {str(e)}'}), 500

        @self.app.route('/api/system/restart', methods=['POST'])
        def api_restart_system():
            """重启系统"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                import os
                import sys

                self.logger.web.info("收到重启请求，正在重启系统...")

                # 延迟重启，给前端时间接收响应
                def restart_delayed():
                    try:
                        asyncio.run(self.config_manager.flush_dirty_configs())
                        asyncio.run(reboot(wait_seconds=2))
                    except Exception as e:
                        self.logger.web.error(f"重启前写盘失败: {e}")

                import threading
                threading.Thread(target=restart_delayed, daemon=True).start()

                return jsonify({'success': True, 'message': '系统将在2秒后重启'})
            except Exception as e:
                self.logger.web.error(f"重启系统失败: {e}")
                return jsonify({'error': f'重启系统失败: {str(e)}'}), 500

        @self.app.route('/api/logs')
        def api_logs():
            """获取日志文件列表"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                from pathlib import Path
                import re
                logs_dir = Path("logs")

                if not logs_dir.exists():
                    return jsonify({'files': []})

                log_files = []

                # 递归扫描logs目录及其子目录
                for log_file in logs_dir.rglob("*"):
                    if log_file.is_file():
                        # 匹配.log文件和轮转文件（.log.日期格式）
                        if log_file.name.endswith('.log') or re.match(r'.*\.log\.\d{4}-\d{2}-\d{2}$', log_file.name):
                            stat = log_file.stat()

                            # 计算相对路径
                            relative_path = log_file.relative_to(logs_dir)

                            # 判断是否为轮转文件
                            is_rotated = not log_file.name.endswith('.log')

                            # 获取日志类型（根据目录结构）
                            log_type = str(relative_path.parent) if relative_path.parent != Path('.') else 'main'

                            log_files.append({
                                'name': str(relative_path),
                                'display_name': log_file.name,
                                'size': stat.st_size,
                                'modified': stat.st_mtime,
                                'is_rotated': is_rotated,
                                'log_type': log_type
                            })

                # 按类型分组，非轮转文件优先，然后按修改时间排序
                log_files.sort(key=lambda x: (x['is_rotated'], -x['modified']))

                return jsonify({'files': log_files})
            except Exception as e:
                self.logger.web.error(f"获取日志文件列表失败: {e}")
                return jsonify({'error': f'获取日志文件列表失败: {str(e)}'}), 500

        @self.app.route('/api/logs/<path:filename>')
        def api_log_content(filename):
            """获取日志文件内容"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                from pathlib import Path
                import os

                # 安全检查，防止路径遍历攻击
                if '..' in filename:
                    return jsonify({'error': '无效的文件名'}), 400

                log_file = Path("logs") / filename

                if not log_file.exists():
                    return jsonify({'error': '日志文件不存在'}), 404

                # 确保文件在logs目录内
                if not str(log_file.resolve()).startswith(str(Path("logs").resolve())):
                    return jsonify({'error': '无效的文件路径'}), 400

                # 获取查询参数
                lines = int(request.args.get('lines', 1000))  # 默认显示最后1000行

                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content_lines = f.readlines()

                    # 只返回最后N行
                    if len(content_lines) > lines:
                        content_lines = content_lines[-lines:]

                    return jsonify({
                        'content': ''.join(content_lines),
                        'total_lines': len(content_lines),
                        'file_size': log_file.stat().st_size
                    })
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，尝试其他编码
                    with open(log_file, 'r', encoding='gbk') as f:
                        content_lines = f.readlines()

                    if len(content_lines) > lines:
                        content_lines = content_lines[-lines:]

                    return jsonify({
                        'content': ''.join(content_lines),
                        'total_lines': len(content_lines),
                        'file_size': log_file.stat().st_size
                    })

            except Exception as e:
                self.logger.web.error(f"获取日志文件内容失败: {e}")
                return jsonify({'error': f'获取日志文件内容失败: {str(e)}'}), 500
            
            
        @self.app.route('/api/statistics')
        def api_statistics():
            """统计数据API - 修复版本"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 获取查询参数
                range_param = request.args.get('range', 'week')
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                self_id = request.args.get('self_id')
                direction = request.args.get('direction', 'SEND')    
                now = datetime.now(timezone.utc)
                
                if range_param == 'today':
                    start_time = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
                    end_time = int(now.timestamp())
                elif range_param == 'yesterday':
                    yesterday = now - timedelta(days=1)
                    start_time = int(yesterday.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
                    end_time = int(yesterday.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp())
                elif range_param == 'week':
                    start_time = int((now - timedelta(days=7)).timestamp())
                    end_time = int(now.timestamp())
                elif range_param == 'month':
                    start_time = int((now - timedelta(days=30)).timestamp())
                    end_time = int(now.timestamp())
                elif range_param == 'custom' and start_date and end_date:
                    try:
                        start_date_clean = start_date.strip()
                        end_date_clean = end_date.strip()
                        
                        def parse_date_string(date_str):
                            if 'T' in date_str:
                                if date_str.endswith('Z'):
                                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                else:
                                    dt = datetime.fromisoformat(date_str)
                                    if dt.tzinfo is None:
                                        dt = dt.replace(tzinfo=timezone.utc)
                                    return dt
                            else:
                                dt = datetime.strptime(date_str, '%Y-%m-%d')
                                return dt.replace(tzinfo=timezone.utc)
                        
                        start_dt = parse_date_string(start_date_clean)
                        end_dt = parse_date_string(end_date_clean)
                        
                        if start_dt.hour == 0 and start_dt.minute == 0 and start_dt.second == 0:
                            pass
                        else:
                            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                        
                        if end_dt.hour == 23 and end_dt.minute == 59:
                            pass
                        else:
                            # 设置为当天结束
                            end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                        
                        start_time = int(start_dt.timestamp())
                        end_time = int(end_dt.timestamp())
                        
                        # 调试日志
                        self.logger.web.info(f"自定义日期范围: {start_date} -> {start_dt} ({start_time})")
                        self.logger.web.info(f"自定义日期范围: {end_date} -> {end_dt} ({end_time})")
                        
                    except (ValueError, TypeError) as e:
                        self.logger.web.error(f"解析自定义日期失败: {e}, start_date={start_date}, end_date={end_date}")
                        # 回退到默认的7天范围
                        start_time = int((now - timedelta(days=7)).timestamp())
                        end_time = int(now.timestamp())
                else:
                    # 默认最近7天
                    start_time = int((now - timedelta(days=7)).timestamp())
                    end_time = int(now.timestamp())
                    
                # 验证时间范围的合理性
                if start_time >= end_time:
                    self.logger.web.warning(f"无效的时间范围: start_time={start_time}, end_time={end_time}")
                    # 回退到默认范围
                    start_time = int((now - timedelta(days=7)).timestamp())
                    end_time = int(now.timestamp())
                    
                # 获取基本统计
                total_messages = asyncio.run(
                    self.database_manager.count_messages(
                        self_id=self_id,
                        start_time=start_time,
                        end_time=end_time,
                        direction=direction
                    )
                )

                # 获取活跃用户数（发送消息的用户）
                user_stats = asyncio.run(
                    self.database_manager.count_messages_group_by_user_id(
                        self_id=self_id,
                        start_time=start_time,
                        end_time=end_time,
                        direction=direction
                    )
                )
                active_users = len(user_stats)

                # 获取活跃群组数
                group_stats = asyncio.run(
                    self.database_manager.count_messages_group_by_group_id(
                        self_id=self_id,
                        start_time=start_time,
                        end_time=end_time,
                        direction=direction
                    )
                )
                active_groups = len(group_stats)

                # 获取昨日同期数据用于对比
                time_range_duration = end_time - start_time
                yesterday_start = start_time - time_range_duration
                yesterday_end = end_time - time_range_duration

                yesterday_messages = asyncio.run(
                    self.database_manager.count_messages(
                        self_id=self_id,
                        start_time=yesterday_start,
                        end_time=yesterday_end,
                        direction=direction
                    )
                )

                yesterday_user_stats = asyncio.run(
                    self.database_manager.count_messages_group_by_user_id(
                        self_id=self_id,
                        start_time=yesterday_start,
                        end_time=yesterday_end,
                        direction=direction
                    )
                )
                yesterday_users = len(yesterday_user_stats)

                yesterday_group_stats = asyncio.run(
                    self.database_manager.count_messages_group_by_group_id(
                        self_id=self_id,
                        start_time=yesterday_start,
                        end_time=yesterday_end,
                        direction=direction
                    )
                )
                yesterday_groups = len(yesterday_group_stats)

                # 获取每3小时的消息趋势
                hourly_trend = asyncio.run(
                    self.database_manager.count_messages_by_time_intervals(
                        self_id=self_id,
                        start_time=start_time,
                        end_time=end_time,
                        interval_hours=3,
                        direction=direction
                    )
                )

                # 获取收到的消息总量（RECV方向）
                received_messages = asyncio.run(
                    self.database_manager.count_messages(
                        self_id=self_id,
                        start_time=start_time,
                        end_time=end_time,
                        direction="RECV"
                    )
                )

                # 获取昨日收到的消息数量用于对比
                yesterday_received_messages = asyncio.run(
                    self.database_manager.count_messages(
                        self_id=self_id,
                        start_time=yesterday_start,
                        end_time=yesterday_end,
                        direction="RECV"
                    )
                )

                # 构建响应数据
                stats = {
                    'total_messages': total_messages,
                    'active_users': active_users,
                    'active_groups': active_groups,
                    'received_messages': received_messages,
                    'hourly_trend': hourly_trend,
                    'top_groups': [
                        {
                            'group_id': group_id,
                            'message_count': count,
                            'active_users': 1
                        }
                        for group_id, count in sorted(group_stats.items(), key=lambda x: x[1], reverse=True)
                    ],
                    # 添加变化指示器
                    'messages_change': total_messages - yesterday_messages,
                    'users_change': active_users - yesterday_users,
                    'groups_change': active_groups - yesterday_groups,
                    'received_change': received_messages - yesterday_received_messages,
                    # 添加调试信息（可选）
                    'debug_info': {
                        'start_time': start_time,
                        'end_time': end_time,
                        'start_date_parsed': datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
                        'end_date_parsed': datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat()
                    }
                }

                return jsonify(stats)
            except Exception as e:
                self.logger.web.error(f"获取统计数据失败: {e}")
                return jsonify({'error': f'获取统计数据失败: {str(e)}'}), 500

        @self.app.route('/api/query_messages')
        def api_query_messages():
            """消息查询API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 获取查询参数
                self_id = request.args.get('self_id') or None
                user_id = request.args.get('user_id') or None
                group_id = request.args.get('group_id') or None

                # 处理特殊值：__private__ 表示只查询私聊消息（group_id为None）
                private_only = False
                if group_id == '__private__':
                    private_only = True
                    group_id = None
                start_time = request.args.get('start_time')
                end_time = request.args.get('end_time')
                keywords = request.args.getlist('keywords')
                keyword_type = request.args.get('keyword_type', 'and')
                prefix = request.args.get('prefix') or None
                direction = request.args.get('direction') or None
                limit = int(request.args.get('limit', 20))
                offset = int(request.args.get('offset', 0))

                # 转换时间戳
                start_time_int = int(start_time) if start_time else None
                end_time_int = int(end_time) if end_time else None

                # 异步调用查询
                messages = asyncio.run(
                    self.database_manager.query_messages_combined(
                        self_id=self_id,
                        user_id=user_id,
                        group_id=group_id,
                        start_time=start_time_int,
                        end_time=end_time_int,
                        keywords=keywords if keywords else None,
                        keyword_type=keyword_type,
                        prefix=prefix,
                        direction=direction,
                        limit=limit,
                        offset=offset,
                        private_only=private_only
                    )
                )

                # 获取总数
                total_count = asyncio.run(
                    self.database_manager.count_messages(
                        self_id=self_id,
                        user_id=user_id,
                        group_id=group_id,
                        start_time=start_time_int,
                        end_time=end_time_int,
                        keywords=keywords if keywords else None,
                        keyword_type=keyword_type,
                        prefix=prefix,
                        direction=direction,
                        private_only=private_only
                    )
                )

                # 转换消息记录为字典
                message_dicts = []
                for msg in messages:
                    message_dicts.append({
                        'id': msg.id,
                        'message_id': msg.message_id,
                        'self_id': msg.self_id,
                        'user_id': msg.user_id,
                        'group_id': msg.group_id,
                        'message_type': msg.message_type,
                        'sub_type': msg.sub_type,
                        'post_type': msg.post_type,
                        'raw_message': msg.raw_message,
                        'message_content': msg.message_content,
                        'sender_info': msg.sender_info,
                        'timestamp': msg.timestamp,
                        'direction': msg.direction,
                        'connection_id': msg.connection_id
                    })

                return jsonify({
                    'messages': message_dicts,
                    'total_count': total_count,
                    'offset': offset,
                    'limit': limit
                })

            except Exception as e:
                self.logger.web.error(f"查询消息失败: {e}")
                return jsonify({'error': f'查询消息失败: {str(e)}'}), 500


        @self.app.route('/api/statistics/database')
        def api_database_statistics():
            """数据库统计API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 获取查询参数
                self_id = request.args.get('self_id')
                start_time = request.args.get('start_time')
                end_time = request.args.get('end_time')

                # 转换时间戳
                start_time_int = int(start_time) if start_time else None
                end_time_int = int(end_time) if end_time else None

                # 按群组统计消息数量（只统计群组消息，排除私聊）
                all_group_stats = asyncio.run(
                    self.database_manager.count_messages_group_by_group_id(
                        self_id=self_id,
                        start_time=start_time_int,
                        end_time=end_time_int,
                        direction="SEND"
                    )
                )

                # 过滤掉私聊消息（group_id为None或空的）
                group_stats = {k: v for k, v in all_group_stats.items() if k and k.strip()}

                # 按账号统计消息数量
                account_stats = asyncio.run(
                    self.database_manager.count_messages_group_by_self_id(
                        start_time=start_time_int,
                        end_time=end_time_int,
                        direction="SEND"
                    )
                )

                # 按用户统计消息数量
                user_stats = asyncio.run(
                    self.database_manager.count_messages_group_by_user_id(
                        self_id=self_id,
                        start_time=start_time_int,
                        end_time=end_time_int,
                        direction="SEND"
                    )
                )

                return jsonify({
                    'group_statistics': group_stats,
                    'account_statistics': account_stats,
                    'user_statistics': user_stats
                })

            except Exception as e:
                self.logger.web.error(f"获取数据库统计失败: {e}")
                return jsonify({'error': f'获取数据库统计失败: {str(e)}'}), 500

        @self.app.route('/api/recently-active-accounts')
        def api_recently_active_accounts():
            """获取今日活跃账号API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                active_accounts = asyncio.run(self.config_manager.get_recently_active_accounts(hours=24))
                return jsonify(active_accounts)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/recently-active-groups')
        def api_recently_active_groups():
            """获取今日活跃群组API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                active_groups = asyncio.run(self.config_manager.get_recently_active_groups(hours=24))
                return jsonify(active_groups)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/accounts')
        def api_accounts():
            """账号管理API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 先落盘脏数据，再重新加载账号配置以获取最新数据
                asyncio.run(self.config_manager.flush_dirty_configs())
                asyncio.run(self.config_manager._load_account_configs())
                accounts = self.config_manager.get_all_account_configs()
                return jsonify(accounts)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/accounts/<account_id>/online-status', methods=['GET'])
        def api_account_online_status(account_id):
            """检查账号在线状态（通过向连接发送get_status API）"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                if not self.proxy_server:
                    return jsonify({'online': False}), 200

                future = asyncio.run_coroutine_threadsafe(
                    self.proxy_server.check_account_online_status(int(account_id)),
                    self.loop
                )
                online = future.result(timeout=5.0)
                return jsonify({'online': online}), 200

            except concurrent.futures.TimeoutError:
                self.logger.web.warning(f"检查账号{account_id}在线状态超时")
                return jsonify({'online': False, 'error': 'timeout'}), 200
            except Exception as e:
                self.logger.web.error(f"检查账号在线状态失败: {e}")
                return jsonify({'online': False, 'error': str(e)}), 200

        @self.app.route('/api/accounts/<account_id>', methods=['PUT'])
        def api_update_account(account_id):
            """更新账号配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                config = request.get_json()
                
                original_config = asyncio.run(self.config_manager.get_account_config(account_id))
                if not original_config:
                    return jsonify({'error': '账号不存在'}), 404
                
                # 只允许更新现有的字段
                for k, v in config.items():
                    if k in original_config:
                        original_config[k] = v

                asyncio.run(
                    self.config_manager.save_account_config(account_id, original_config)
                )
                asyncio.run(self.config_manager.flush_dirty_configs())
                return jsonify({'success': True})
            except ValueError as e:
                self.logger.web.warning(f"账号配置验证失败: {e}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.web.error(f"更新账号配置失败: {e}")
                return jsonify({'error': f'更新账号配置失败: {str(e)}'}), 500
            
        @self.app.route('/api/accounts/<account_id>', methods=['DELETE'])
        def api_delete_account(account_id):
            """删除账号配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 在新的事件循环中运行异步操作
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.config_manager.delete_account_config(account_id)
                    )
                finally:
                    loop.close()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/groups')
        def api_groups():
            """群组管理API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 先落盘脏数据，再重新加载群组配置以获取最新数据
                asyncio.run(self.config_manager.flush_dirty_configs())
                asyncio.run(self.config_manager._load_group_configs())
                groups = self.config_manager.get_all_group_configs()
                return jsonify(groups)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/config/flush', methods=['POST'])
        def api_flush_config():
            """立即将内存中的脏配置写入磁盘"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                asyncio.run(self.config_manager.flush_dirty_configs())
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/groups/<group_id>', methods=['PUT'])
        def api_update_group(group_id):
            """更新群组配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                config = request.get_json()

                original_config = asyncio.run(self.config_manager.get_group_config(group_id))
                
                # 只允许更新现有的字段
                for k, v in config.items():
                    if k in original_config:
                        original_config[k] = v

                # 运行异步操作
                asyncio.run(
                    self.config_manager.save_group_config(group_id, original_config)
                )
                asyncio.run(self.config_manager.flush_dirty_configs())
                return jsonify({'success': True})
            except ValueError as e:
                self.logger.web.warning(f"群组配置验证失败: {e}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.web.error(f"更新群组配置失败: {e}")
                return jsonify({'error': f'更新群组配置失败: {str(e)}'}), 500

        @self.app.route('/api/connections/<connection_id>/copy', methods=['POST'])
        def api_copy_connection(connection_id):
            """复制连接配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                data = request.get_json()
                new_connection_id = data.get('new_id')
                new_name = data.get('new_name')

                if not new_connection_id:
                    return jsonify({'error': '缺少新连接ID'}), 400

                # 获取原配置
                original_config = self.config_manager.get_connection_config(connection_id)
                if not original_config:
                    return jsonify({'error': '原连接配置不存在'}), 404

                # 复制配置并修改名称
                new_config = original_config.copy()
                # 使用传入的新名称，如果没有则使用默认格式
                if new_name:
                    new_config['name'] = new_name
                else:
                    new_config['name'] = "{} - 副本".format(original_config.get('name', '连接'))
                new_config['enabled'] = False

                # 保存新配置
                asyncio.run(
                    self.config_manager.save_connection_config(new_connection_id, new_config)
                )

                return jsonify({'success': True, 'message': '连接配置已复制'})
            except ValueError as e:
                self.logger.web.warning(f"复制连接配置验证失败: {e}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.web.error(f"复制连接配置失败: {e}")
                return jsonify({'error': f'复制连接配置失败: {str(e)}'}), 500

        @self.app.route('/api/connections/<connection_id>', methods=['DELETE'])
        def api_delete_connection(connection_id):
            """删除连接配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 在新的事件循环中运行异步操作
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.config_manager.delete_connection_config(connection_id)
                    )
                finally:
                    loop.close()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/groups/<group_id>', methods=['DELETE'])
        def api_delete_group(group_id):
            """删除群组配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 在新的事件循环中运行异步操作
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.config_manager.delete_group_config(group_id)
                    )
                finally:
                    loop.close()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/blacklist')
        def api_blacklist():
            """黑名单API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                # 重新加载全局配置以获取最新黑名单数据
                asyncio.run(self.config_manager._load_global_config())
                global_config = self.config_manager.get_global_config()
                blacklist = global_config.get('blacklist', {'users': [], 'groups': []})
                return jsonify(blacklist)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/blacklist', methods=['POST'])
        def api_add_blacklist():
            """添加黑名单"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                data = request.get_json()
                item_type = data.get('type')  # 'users' or 'groups'
                item_id = data.get('id')

                if item_type not in ['users', 'groups']:
                    return jsonify({'error': '无效的类型'}), 400

                # 运行异步操作
                asyncio.run(
                    self.config_manager.add_to_blacklist(item_type, item_id)
                )
                return jsonify({'success': True})
            except Exception as e:
                self.logger.web.error(f"添加黑名单失败: {e}")
                return jsonify({'error': f'添加黑名单失败: {str(e)}'}), 500

        @self.app.route('/api/blacklist', methods=['DELETE'])
        def api_remove_blacklist():
            """移除黑名单"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                data = request.get_json()
                item_type = data.get('type')  # 'users' or 'groups'
                item_id = data.get('id')

                if item_type not in ['users', 'groups']:
                    return jsonify({'error': '无效的类型'}), 400

                # 运行异步操作
                asyncio.run(
                    self.config_manager.remove_from_blacklist(item_type, item_id)
                )
                return jsonify({'success': True})
            except Exception as e:
                self.logger.web.error(f"移除黑名单失败: {e}")
                return jsonify({'error': f'移除黑名单失败: {str(e)}'}), 500

        @self.app.route('/api/backups')
        def api_list_backups():
            """列出所有备份文件"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                backup_manager = self.proxy_server.backup_manager
                if not backup_manager:
                    return jsonify({'error': '备份管理器未初始化'}), 500

                backups = backup_manager.list_backups()
                return jsonify({'backups': backups})
            except Exception as e:
                self.logger.web.error(f"列出备份失败: {e}")
                return jsonify({'error': f'列出备份失败: {str(e)}'}), 500

        @self.app.route('/api/backups/<filename>')
        def api_download_backup(filename):
            """下载备份文件"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                backup_manager = self.proxy_server.backup_manager
                if not backup_manager:
                    return jsonify({'error': '备份管理器未初始化'}), 500

                # 获取备份文件路径
                backup_path = backup_manager.get_backup_path(filename)
                if not backup_path:
                    return jsonify({'error': '备份文件不存在'}), 404

                # 发送文件
                from flask import send_file
                return send_file(backup_path, as_attachment=True, download_name=filename)
            except Exception as e:
                self.logger.web.error(f"下载备份失败: {e}")
                return jsonify({'error': f'下载备份失败: {str(e)}'}), 500

        @self.app.route('/api/backups', methods=['POST'])
        def api_create_backup():
            """创建新备份"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                backup_manager = self.proxy_server.backup_manager
                if not backup_manager:
                    return jsonify({'error': '备份管理器未初始化'}), 500

                # 获取密码
                global_config = self.config_manager.get_global_config()
                web_auth = global_config.get("web_auth", {})
                password = web_auth.get("password", "admin")

                # 创建备份
                backup_path = backup_manager.create_backup(password)
                if not backup_path:
                    return jsonify({'error': '备份创建失败'}), 500

                # 获取文件信息
                import os
                filename = os.path.basename(backup_path)
                file_size = os.path.getsize(backup_path)

                return jsonify({
                    'success': True,
                    'filename': filename,
                    'size': file_size
                })
            except Exception as e:
                self.logger.web.error(f"创建备份失败: {e}")
                return jsonify({'error': f'创建备份失败: {str(e)}'}), 500

        @self.app.route('/api/backups/<filename>', methods=['DELETE'])
        def api_delete_backup(filename):
            """删除备份文件"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                backup_manager = self.proxy_server.backup_manager
                if not backup_manager:
                    return jsonify({'error': '备份管理器未初始化'}), 500

                # 获取备份文件路径
                backup_path = backup_manager.get_backup_path(filename)
                if not backup_path:
                    return jsonify({'error': '备份文件不存在'}), 404

                # 删除文件
                import os
                os.remove(backup_path)

                return jsonify({'success': True})
            except Exception as e:
                self.logger.web.error(f"删除备份失败: {e}")
                return jsonify({'error': f'删除备份失败: {str(e)}'}), 500

    def _check_auth(self) -> bool:
        """检查认证状态"""
        return session.get('authenticated', False)
    
    async def start(self):
        """启动Web服务器"""
        self.running = True
        self.logger.web.info("启动Web服务器...")
        
        # 在单独线程中运行Flask应用
        def run_server():
            serve(self.app, host='0.0.0.0', port=self.port, threads=4)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        self.logger.web.info(f"WebUI已启动在 http://localhost:{self.port}")
        
        # 保持运行状态
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """停止Web服务器"""
        self.running = False
        self.logger.web.info("正在停止Web服务器...")
        
        # TODO: 优雅关闭Waitress服务器
        
        self.logger.web.info("Web服务器已停止")
