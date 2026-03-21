// Dashboard JavaScript

// API base URL
const API_BASE = '';

// Current section
let currentSection = 'overview';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadOverview();
    checkHealth();
});

// Navigation
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            navigateTo(section);
        });
    });
}

function navigateTo(section) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });

    // Update section
    document.querySelectorAll('.section').forEach(s => {
        s.classList.toggle('active', s.id === `section-${section}`);
    });

    // Update title
    const titles = {
        overview: '概览',
        content: '内容创作',
        publish: '发布管理',
        platforms: '平台管理',
        tasks: '任务队列',
        analytics: '数据分析'
    };
    document.getElementById('page-title').textContent = titles[section] || section;

    currentSection = section;

    // Load section data
    switch (section) {
        case 'overview':
            loadOverview();
            break;
        case 'content':
            loadDrafts();
            break;
        case 'platforms':
            loadPlatforms();
            break;
        case 'tasks':
            loadTasks();
            break;
        case 'analytics':
            loadAnalytics();
            break;
    }
}

// API helpers
async function apiGet(endpoint) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`);
        return await res.json();
    } catch (error) {
        console.error(`API Error: ${endpoint}`, error);
        return null;
    }
}

async function apiPost(endpoint, data) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await res.json();
    } catch (error) {
        console.error(`API Error: ${endpoint}`, error);
        return null;
    }
}

// Health check
async function checkHealth() {
    const result = await apiGet('/health');
    const statusText = document.querySelector('.status-text');
    const dot = document.querySelector('.dot');

    if (result && result.status === 'healthy') {
        statusText.textContent = '服务正常';
        dot.style.background = 'var(--success)';
    } else {
        statusText.textContent = '服务异常';
        dot.style.background = 'var(--error)';
    }
}

// Load Overview
async function loadOverview() {
    // Load stats
    const overview = await apiGet('/analytics/overview');
    if (overview) {
        document.getElementById('stat-posts').textContent = overview.total_posts || '-';
        document.getElementById('stat-views').textContent = formatNumber(overview.total_views) || '-';
        document.getElementById('stat-engagement').textContent = formatNumber(overview.total_engagement) || '-';
        document.getElementById('stat-followers').textContent = overview.followers_gained || '-';
    }

    // Load trending
    const trending = await apiGet('/analytics/trending');
    const trendingList = document.getElementById('trending-list');
    if (trending && trending.topics) {
        trendingList.innerHTML = trending.topics.map(t => `
            <div class="trending-item">
                <span class="trending-rank">${t.rank}</span>
                <span class="trending-topic">${t.topic}</span>
                <span class="trending-heat">
                    🔥 ${t.heat}
                    <span class="trend-${t.trend}">${t.trend === 'up' ? '↑' : t.trend === 'down' ? '↓' : '→'}</span>
                </span>
            </div>
        `).join('');
    } else {
        trendingList.innerHTML = '<div class="empty-state">暂无热点数据</div>';
    }

    // Load platform stats
    const platformStats = await apiGet('/analytics/platforms');
    const chartContainer = document.getElementById('platform-chart');
    if (platformStats && platformStats.platforms) {
        chartContainer.innerHTML = platformStats.platforms.map(p => `
            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                <span>${p.platform}</span>
                <span>${formatNumber(p.views)} 浏览</span>
            </div>
        `).join('');
    }
}

// Load Drafts
async function loadDrafts() {
    const draftsList = document.getElementById('drafts-list');
    const result = await apiGet('/content/drafts');

    if (result && result.drafts && result.drafts.length > 0) {
        draftsList.innerHTML = result.drafts.map(d => `
            <div class="content-item">
                <div class="content-info">
                    <h4>${d.title}</h4>
                    <div class="content-meta">
                        <span>${d.platform_name}</span>
                        <span>${formatDate(d.created_at)}</span>
                        <span>${d.word_count} 字</span>
                    </div>
                </div>
                <div class="content-actions">
                    <button class="btn btn-secondary" onclick="editDraft('${d.id}')">编辑</button>
                    <button class="btn btn-primary" onclick="publishDraft('${d.id}')">发布</button>
                    <button class="btn btn-secondary" onclick="deleteDraft('${d.id}')">删除</button>
                </div>
            </div>
        `).join('');
    } else {
        draftsList.innerHTML = '<div class="empty-state">暂无草稿，点击"新建内容"开始创作</div>';
    }
}

// Load Platforms
async function loadPlatforms() {
    const result = await apiGet('/content/platforms');
    const domesticContainer = document.getElementById('domestic-platforms');
    const overseasContainer = document.getElementById('overseas-platforms');

    if (result) {
        if (result.domestic) {
            domesticContainer.innerHTML = result.domestic.map(p => `
                <div class="platform-item">
                    <span>🌐</span>
                    <span class="platform-name">${p.name}</span>
                    <span class="platform-status">${p.status}</span>
                </div>
            `).join('');
        }
        if (result.overseas) {
            overseasContainer.innerHTML = result.overseas.map(p => `
                <div class="platform-item">
                    <span>🌍</span>
                    <span class="platform-name">${p.name}</span>
                    <span class="platform-status">${p.status}</span>
                </div>
            `).join('');
        }
    }
}

// Load Tasks
async function loadTasks() {
    const tasksList = document.getElementById('tasks-list');
    const result = await apiGet('/tasks/');

    if (result && result.tasks && result.tasks.length > 0) {
        tasksList.innerHTML = result.tasks.map(t => `
            <div class="task-item">
                <div class="task-info">
                    <h4>${t.title}</h4>
                    <span class="task-meta">${formatDate(t.created_at)}</span>
                </div>
                <span class="task-status status-${t.status}">${getStatusLabel(t.status)}</span>
            </div>
        `).join('');
    } else {
        tasksList.innerHTML = '<div class="empty-state">暂无任务</div>';
    }
}

// Load Analytics
async function loadAnalytics() {
    const container = document.getElementById('analytics-detail');
    const overview = await apiGet('/analytics/overview');
    const platformStats = await apiGet('/analytics/platforms');

    if (overview && platformStats) {
        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📝</div>
                    <div class="stat-info">
                        <span class="stat-value">${overview.total_posts}</span>
                        <span class="stat-label">总发布</span>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">👀</div>
                    <div class="stat-info">
                        <span class="stat-value">${formatNumber(overview.total_views)}</span>
                        <span class="stat-label">总浏览</span>
                    </div>
                </div>
            </div>
            <h4 style="margin-top: 1.5rem; margin-bottom: 1rem;">平台数据</h4>
            ${platformStats.platforms.map(p => `
                <div style="padding: 1rem; background: var(--bg-hover); border-radius: 0.5rem; margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <strong>${p.platform}</strong>
                        <span>${formatNumber(p.views)} 浏览</span>
                    </div>
                    <div style="display: flex; gap: 1rem; font-size: 0.875rem; color: var(--text-secondary);">
                        <span>❤️ ${p.likes}</span>
                        <span>💬 ${p.comments}</span>
                        <span>🔄 ${p.shares}</span>
                    </div>
                </div>
            `).join('')}
        `;
    }
}

// Modal functions
function showGenerateModal() {
    const modal = document.getElementById('generate-modal');
    modal.classList.add('active');
    loadPlatformsForModal();
}

function closeModal() {
    document.getElementById('generate-modal').classList.remove('active');
    document.getElementById('generate-form').reset();
}

async function loadPlatformsForModal() {
    const result = await apiGet('/content/platforms');
    const container = document.getElementById('platform-checkboxes');

    if (result) {
        const allPlatforms = [
            ...(result.domestic || []),
            ...(result.overseas || [])
        ];
        container.innerHTML = allPlatforms.map(p => `
            <label class="platform-checkbox">
                <input type="checkbox" name="platforms" value="${p.id}">
                <span>${p.name}</span>
            </label>
        `).join('');
    }
}

// Form submission
document.getElementById('generate-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const topic = document.getElementById('topic').value;
    const keywords = document.getElementById('keywords').value.split(',').map(k => k.trim()).filter(k => k);
    const selectedPlatforms = Array.from(document.querySelectorAll('input[name="platforms"]:checked')).map(cb => cb.value);
    const tone = document.getElementById('tone').value;

    if (selectedPlatforms.length === 0) {
        showToast('请选择至少一个目标平台', 'error');
        return;
    }

    const result = await apiPost('/content/generate', {
        topic,
        keywords,
        target_platforms: selectedPlatforms,
        tone
    });

    if (result && result.success) {
        showToast(`成功生成 ${result.drafts.length} 篇内容`, 'success');
        closeModal();
        if (currentSection === 'content') {
            loadDrafts();
        }
    } else {
        showToast('生成失败，请重试', 'error');
    }
});

// Draft actions
async function deleteDraft(contentId) {
    if (!confirm('确定要删除这篇草稿吗？')) return;

    const result = await apiFetch(`/content/drafts/${contentId}`, { method: 'DELETE' });
    if (result) {
        showToast('草稿已删除', 'success');
        loadDrafts();
    }
}

async function publishDraft(contentId) {
    showToast('发布功能待实现', 'error');
}

function editDraft(contentId) {
    showToast('编辑功能待实现', 'error');
}

// Helper functions
async function apiFetch(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, options);
        return await res.json();
    } catch (error) {
        console.error(`API Error: ${endpoint}`, error);
        return null;
    }
}

function formatNumber(num) {
    if (!num) return '-';
    if (num >= 10000) return (num / 10000).toFixed(1) + 'w';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = (now - date) / 1000;

    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
    return date.toLocaleDateString('zh-CN');
}

function getStatusLabel(status) {
    const labels = {
        pending: '等待中',
        running: '进行中',
        completed: '已完成',
        failed: '失败'
    };
    return labels[status] || status;
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
