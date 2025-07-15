// BotShepherd WebUI JavaScript

let connections = {};
let selectedConnectionId = null;
let editingConnectionId = null;
let deleteConnectionId = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadConnections();
    refreshStatus();
    
    // 定期刷新状态
    setInterval(refreshStatus, 5000);
});

// 加载所有连接配置
async function loadConnections() {
    try {
        const response = await fetch('/api/connections');
        const result = await response.json();
        
        if (result.success) {
            connections = result.data;
            renderConnectionsList();
            updateConnectionsCount();
        } else {
            showToast('加载连接配置失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
    }
}

// 渲染连接列表
function renderConnectionsList() {
    const container = document.getElementById('connections-list');
    container.innerHTML = '';
    
    if (Object.keys(connections).length === 0) {
        container.innerHTML = '<p class="text-muted">暂无连接配置</p>';
        return;
    }
    
    for (const [connectionId, config] of Object.entries(connections)) {
        const connectionItem = createConnectionItem(connectionId, config);
        container.appendChild(connectionItem);
    }
}

// 创建连接项元素
function createConnectionItem(connectionId, config) {
    const div = document.createElement('div');
    div.className = `connection-item ${config.enabled ? '' : 'disabled'}`;
    div.onclick = () => selectConnection(connectionId);
    
    const statusClass = config.enabled ? 'status-running' : 'status-disabled';
    const statusText = config.enabled ? '启用' : '禁用';
    
    div.innerHTML = `
        <div class="connection-header">
            <h6 class="connection-name">${config.name}</h6>
            <span class="connection-status ${statusClass}">${statusText}</span>
        </div>
        <div class="connection-endpoints">
            <div class="endpoint-item">
                <span class="endpoint-label">客户端:</span> ${config.client_endpoint}
            </div>
            <div class="endpoint-item">
                <span class="endpoint-label">目标:</span> ${Array.isArray(config.target_endpoints) ? config.target_endpoints.join(', ') : (config.target_endpoint || '未配置')}
            </div>
        </div>
        <div class="connection-actions" onclick="event.stopPropagation()">
            <button class="btn btn-outline-primary btn-sm" onclick="editConnection('${connectionId}')">
                <i class="bi bi-pencil"></i> 编辑
            </button>
            <button class="btn btn-outline-success btn-sm" onclick="startProxy('${connectionId}')" 
                    ${!config.enabled ? 'disabled' : ''}>
                <i class="bi bi-play"></i> 启动
            </button>
            <button class="btn btn-outline-warning btn-sm" onclick="stopProxy('${connectionId}')">
                <i class="bi bi-stop"></i> 停止
            </button>
            <button class="btn btn-outline-danger btn-sm" onclick="deleteConnection('${connectionId}')">
                <i class="bi bi-trash"></i> 删除
            </button>
        </div>
    `;
    
    return div;
}

// 选择连接
function selectConnection(connectionId) {
    selectedConnectionId = connectionId;
    
    // 更新选中状态
    document.querySelectorAll('.connection-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
    
    // 显示连接详情
    showConnectionDetails(connectionId);
}

// 显示连接详情
function showConnectionDetails(connectionId) {
    const config = connections[connectionId];
    if (!config) return;
    
    const detailsContainer = document.getElementById('connection-details');
    detailsContainer.innerHTML = `
        <div class="connection-details-card">
            <div class="detail-row">
                <span class="detail-label">连接名称:</span>
                <span class="detail-value">${config.name}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">客户端端点:</span>
                <span class="detail-value">${config.client_endpoint}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">目标端点:</span>
                <span class="detail-value">${Array.isArray(config.target_endpoints) ? config.target_endpoints.join('<br>') : (config.target_endpoint || '未配置')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">状态:</span>
                <span class="detail-value">
                    <span class="status-indicator ${config.enabled ? 'online' : 'disabled'}"></span>
                    ${config.enabled ? '启用' : '禁用'}
                </span>
            </div>
            <div class="detail-row">
                <span class="detail-label">描述:</span>
                <span class="detail-value">${config.description || '无'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">创建时间:</span>
                <span class="detail-value">${config.created_at ? new Date(config.created_at).toLocaleString() : '未知'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">更新时间:</span>
                <span class="detail-value">${config.updated_at ? new Date(config.updated_at).toLocaleString() : '未知'}</span>
            </div>
        </div>
    `;
}

// 刷新系统状态
async function refreshStatus() {
    try {
        const response = await fetch('/api/status');
        const result = await response.json();
        
        if (result.success) {
            const status = result.data;
            document.getElementById('active-servers-count').textContent = status.active_servers.length;
            document.getElementById('active-connections-count').textContent = status.active_connections;
            
            // 更新状态指示器
            const statusBadge = document.getElementById('status-badge');
            if (status.active_servers.length > 0) {
                statusBadge.className = 'badge bg-success me-2';
                statusBadge.textContent = '运行中';
            } else {
                statusBadge.className = 'badge bg-secondary me-2';
                statusBadge.textContent = '已停止';
            }
        }
    } catch (error) {
        console.error('Failed to refresh status:', error);
    }
}

// 更新连接数量
function updateConnectionsCount() {
    document.getElementById('total-connections-count').textContent = Object.keys(connections).length;
}

// 显示添加连接模态框
function showAddConnectionModal() {
    editingConnectionId = null;
    document.getElementById('connectionModalTitle').textContent = '添加连接';
    document.getElementById('connectionForm').reset();
    document.getElementById('connectionEnabled').checked = true;

    const modal = new bootstrap.Modal(document.getElementById('connectionModal'));
    modal.show();
}

// 编辑连接
function editConnection(connectionId) {
    editingConnectionId = connectionId;
    const config = connections[connectionId];

    document.getElementById('connectionModalTitle').textContent = '编辑连接';
    document.getElementById('connectionName').value = config.name;
    document.getElementById('clientEndpoint').value = config.client_endpoint;

    // 处理目标端点（支持新旧格式）
    let targetEndpoints = '';
    if (Array.isArray(config.target_endpoints)) {
        targetEndpoints = config.target_endpoints.join('\n');
    } else if (config.target_endpoint) {
        targetEndpoints = config.target_endpoint;
    }
    document.getElementById('targetEndpoints').value = targetEndpoints;

    document.getElementById('connectionDescription').value = config.description || '';
    document.getElementById('connectionEnabled').checked = config.enabled;

    const modal = new bootstrap.Modal(document.getElementById('connectionModal'));
    modal.show();
}

// 保存连接
async function saveConnection() {
    const form = document.getElementById('connectionForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    // 处理目标端点列表
    const targetEndpointsText = document.getElementById('targetEndpoints').value.trim();
    const targetEndpoints = targetEndpointsText.split('\n').map(line => line.trim()).filter(line => line.length > 0);

    const connectionData = {
        name: document.getElementById('connectionName').value,
        client_endpoint: document.getElementById('clientEndpoint').value,
        target_endpoints: targetEndpoints,
        description: document.getElementById('connectionDescription').value,
        enabled: document.getElementById('connectionEnabled').checked
    };

    try {
        let response;
        if (editingConnectionId) {
            // 更新现有连接
            response = await fetch(`/api/connections/${editingConnectionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(connectionData)
            });
        } else {
            // 创建新连接
            response = await fetch('/api/connections', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(connectionData)
            });
        }

        const result = await response.json();

        if (result.success) {
            showToast(editingConnectionId ? '连接更新成功' : '连接创建成功', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('connectionModal'));
            modal.hide();
            loadConnections(); // 重新加载连接列表
        } else {
            showToast('保存失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
    }
}

// 删除连接
function deleteConnection(connectionId) {
    deleteConnectionId = connectionId;
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

// 确认删除
async function confirmDelete() {
    if (!deleteConnectionId) return;

    try {
        const response = await fetch(`/api/connections/${deleteConnectionId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showToast('连接删除成功', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
            modal.hide();

            // 如果删除的是当前选中的连接，清空详情显示
            if (selectedConnectionId === deleteConnectionId) {
                selectedConnectionId = null;
                document.getElementById('connection-details').innerHTML = '<p class="text-muted">请选择一个连接查看详情</p>';
            }

            loadConnections(); // 重新加载连接列表
        } else {
            showToast('删除失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
    }

    deleteConnectionId = null;
}

// 启动代理
async function startProxy(connectionId) {
    try {
        const response = await fetch(`/api/proxy/start/${connectionId}`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showToast('代理服务启动成功', 'success');
            setTimeout(refreshStatus, 1000); // 延迟刷新状态
        } else {
            showToast('启动失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
    }
}

// 停止代理
async function stopProxy(connectionId) {
    try {
        const response = await fetch(`/api/proxy/stop/${connectionId}`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showToast('代理服务停止成功', 'success');
            setTimeout(refreshStatus, 1000); // 延迟刷新状态
        } else {
            showToast('停止失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();

    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';

    const toastHtml = `
        <div id="${toastId}" class="toast ${bgClass} text-white" role="alert">
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();

    // 自动移除
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// 创建提示消息容器
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}
