from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import asyncio
import threading
from typing import Dict, Any
import uuid


class WebAPI:
    """Web API服务器"""
    
    def __init__(self, config_manager, websocket_proxy):
        self.config_manager = config_manager
        self.websocket_proxy = websocket_proxy
        self.app = Flask(__name__, 
                        template_folder='../templates',
                        static_folder='../static')
        CORS(self.app)
        self.setup_routes()
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('index.html')
        
        @self.app.route('/api/connections', methods=['GET'])
        def get_connections():
            """获取所有连接配置"""
            try:
                connections = self.config_manager.get_connections()
                return jsonify({
                    "success": True,
                    "data": connections
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/connections/<connection_id>', methods=['GET'])
        def get_connection(connection_id):
            """获取指定连接配置"""
            try:
                connection = self.config_manager.get_connection(connection_id)
                if connection:
                    return jsonify({
                        "success": True,
                        "data": connection
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Connection not found"
                    }), 404
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/connections', methods=['POST'])
        def create_connection():
            """创建新连接配置"""
            try:
                data = request.get_json()
                
                # 验证必需字段
                required_fields = ['name', 'client_endpoint', 'target_endpoint']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            "success": False,
                            "error": f"Missing required field: {field}"
                        }), 400
                
                # 生成唯一ID
                connection_id = data.get('id', str(uuid.uuid4()))
                
                # 设置默认值
                connection_config = {
                    "name": data['name'],
                    "client_endpoint": data['client_endpoint'],
                    "target_endpoint": data['target_endpoint'],
                    "enabled": data.get('enabled', True),
                    "description": data.get('description', '')
                }
                
                # 保存配置
                if self.config_manager.add_connection(connection_id, connection_config):
                    return jsonify({
                        "success": True,
                        "data": {
                            "id": connection_id,
                            **connection_config
                        }
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to save connection"
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/connections/<connection_id>', methods=['PUT'])
        def update_connection(connection_id):
            """更新连接配置"""
            try:
                data = request.get_json()
                
                # 验证连接是否存在
                existing_connection = self.config_manager.get_connection(connection_id)
                if not existing_connection:
                    return jsonify({
                        "success": False,
                        "error": "Connection not found"
                    }), 404
                
                # 更新配置
                connection_config = {
                    "name": data.get('name', existing_connection['name']),
                    "client_endpoint": data.get('client_endpoint', existing_connection['client_endpoint']),
                    "target_endpoint": data.get('target_endpoint', existing_connection['target_endpoint']),
                    "enabled": data.get('enabled', existing_connection.get('enabled', True)),
                    "description": data.get('description', existing_connection.get('description', ''))
                }
                
                if self.config_manager.update_connection(connection_id, connection_config):
                    return jsonify({
                        "success": True,
                        "data": {
                            "id": connection_id,
                            **connection_config
                        }
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to update connection"
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/connections/<connection_id>', methods=['DELETE'])
        def delete_connection(connection_id):
            """删除连接配置"""
            try:
                if self.config_manager.delete_connection(connection_id):
                    return jsonify({
                        "success": True,
                        "message": "Connection deleted successfully"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Connection not found or failed to delete"
                    }), 404
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/proxy/start/<connection_id>', methods=['POST'])
        def start_proxy(connection_id):
            """启动指定连接的代理服务"""
            try:
                connection_config = self.config_manager.get_connection(connection_id)
                if not connection_config:
                    return jsonify({
                        "success": False,
                        "error": "Connection not found"
                    }), 404
                
                # 在新线程中启动代理服务
                def start_proxy_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.websocket_proxy.start_proxy_server(connection_id, connection_config)
                    )
                
                thread = threading.Thread(target=start_proxy_async)
                thread.daemon = True
                thread.start()
                
                return jsonify({
                    "success": True,
                    "message": f"Proxy server for {connection_id} started"
                })
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/proxy/stop/<connection_id>', methods=['POST'])
        def stop_proxy(connection_id):
            """停止指定连接的代理服务"""
            try:
                # 在新线程中停止代理服务
                def stop_proxy_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.websocket_proxy.stop_proxy_server(connection_id)
                    )
                
                thread = threading.Thread(target=stop_proxy_async)
                thread.daemon = True
                thread.start()
                
                return jsonify({
                    "success": True,
                    "message": f"Proxy server for {connection_id} stopped"
                })
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """获取系统状态"""
            try:
                status = self.websocket_proxy.get_server_status()
                return jsonify({
                    "success": True,
                    "data": status
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/settings', methods=['GET'])
        def get_settings():
            """获取系统设置"""
            try:
                settings = self.config_manager.get_settings()
                return jsonify({
                    "success": True,
                    "data": settings
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/settings', methods=['PUT'])
        def update_settings():
            """更新系统设置"""
            try:
                data = request.get_json()
                if self.config_manager.update_settings(data):
                    return jsonify({
                        "success": True,
                        "message": "Settings updated successfully"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to update settings"
                    }), 500
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

        # 新增统计相关API
        @self.app.route('/api/statistics/<int:self_id>/daily', methods=['GET'])
        def get_daily_statistics(self_id):
            """获取日统计"""
            try:
                date_str = request.args.get('date')
                # 这里需要调用统计功能
                return jsonify({
                    "success": True,
                    "data": {"message": "Statistics API not fully implemented yet"}
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

        @self.app.route('/api/statistics/<int:self_id>/report', methods=['GET'])
        def get_statistics_report(self_id):
            """获取统计报告"""
            try:
                report_type = request.args.get('type', 'daily')
                # 这里需要调用统计报告功能
                return jsonify({
                    "success": True,
                    "data": {"message": "Statistics report API not fully implemented yet"}
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """运行Web服务器"""
        self.app.run(host=host, port=port, debug=debug)
