"""
Web服务器
提供Web管理界面的后端API
"""

import asyncio
import time
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from waitress import serve
import threading
from typing import Dict, Any

class WebServer:
    """Web服务器"""
    
    def __init__(self, config_manager, database_manager, proxy_server, logger):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.proxy_server = proxy_server
        self.logger = logger
        
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

        @self.app.route('/filters')
        def filters():
            """过滤设置页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('filters.html')

        @self.app.route('/settings')
        def settings():
            """系统设置页面"""
            if not self._check_auth():
                return redirect(url_for('login'))
            return render_template('settings.html')
        
        # API路由
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
        
        @self.app.route('/api/connections')
        def api_connections():
            """连接配置API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401
            
            connections = self.config_manager.get_connections_config()
            return jsonify(connections)
        
        @self.app.route('/api/connections/<connection_id>', methods=['PUT'])
        def api_update_connection(connection_id):
            """更新连接配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401
            
            try:
                config = request.get_json()
                asyncio.run(
                    self.config_manager.save_connection_config(connection_id, config)
                )
                return jsonify({'success': True})
            except Exception as e:
                self.logger.web.error(f"更新连接配置失败: {e}")
                return jsonify({'error': f'更新连接配置失败: {str(e)}'}), 500
        
        @self.app.route('/api/global-config')
        def api_global_config():
            """全局配置API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401
            
            config = self.config_manager.get_global_config()
            return jsonify(config)
        
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
            except Exception as e:
                self.logger.web.error(f"更新全局配置失败: {e}")
                return jsonify({'error': f'更新全局配置失败: {str(e)}'}), 500
        
        @self.app.route('/api/statistics')
        def api_statistics():
            """统计数据API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            # 获取查询参数
            date = request.args.get('date')
            self_id = request.args.get('self_id')
            group_id = request.args.get('group_id')
            keyword = request.args.get('keyword')
            command_prefix = request.args.get('command_prefix')

            try:
                # 异步调用统计查询
                stats = asyncio.run(
                    self.database_manager.get_message_statistics(
                        date=date,
                        self_id=self_id,
                        group_id=group_id,
                        keyword=keyword,
                        command_prefix=command_prefix
                    )
                )
                return jsonify(stats)
            except Exception as e:
                self.logger.web.error(f"获取统计数据失败: {e}")
                return jsonify({'error': f'获取统计数据失败: {str(e)}'}), 500

        @self.app.route('/api/accounts')
        def api_accounts():
            """账号管理API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                accounts = self.config_manager.get_all_account_configs()
                return jsonify(accounts)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/accounts/<account_id>', methods=['PUT'])
        def api_update_account(account_id):
            """更新账号配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                config = request.get_json()
                asyncio.run(
                    self.config_manager.save_account_config(account_id, config)
                )
                return jsonify({'success': True})
            except Exception as e:
                self.logger.web.error(f"更新账号配置失败: {e}")
                return jsonify({'error': f'更新账号配置失败: {str(e)}'}), 500

        @self.app.route('/api/groups')
        def api_groups():
            """群组管理API"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                groups = self.config_manager.get_all_group_configs()
                return jsonify(groups)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/groups/<group_id>', methods=['PUT'])
        def api_update_group(group_id):
            """更新群组配置"""
            if not self._check_auth():
                return jsonify({'error': '未授权'}), 401

            try:
                config = request.get_json()
                # 运行异步操作
                asyncio.run(
                    self.config_manager.save_group_config(group_id, config)
                )
                return jsonify({'success': True})
            except Exception as e:
                self.logger.web.error(f"更新群组配置失败: {e}")
                return jsonify({'error': f'更新群组配置失败: {str(e)}'}), 500

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
    
    def _check_auth(self) -> bool:
        """检查认证状态"""
        return session.get('authenticated', False)
    
    async def start(self):
        """启动Web服务器"""
        self.running = True
        self.logger.web.info("启动Web服务器...")
        
        # 在单独线程中运行Flask应用
        def run_server():
            serve(self.app, host='0.0.0.0', port=5000, threads=4)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        self.logger.web.info("Web服务器已启动在 http://localhost:5000")
        
        # 保持运行状态
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """停止Web服务器"""
        self.running = False
        self.logger.web.info("正在停止Web服务器...")
        
        # TODO: 优雅关闭Waitress服务器
        
        self.logger.web.info("Web服务器已停止")
