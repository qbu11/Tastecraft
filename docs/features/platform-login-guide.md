# 平台登录需求与持久化方案

## 需要登录的平台

### 1. 小红书 (Xiaohongshu)
- **登录方式**: 扫码登录 (推荐) / 手机号+验证码
- **Cookie 有效期**: 约 30 天
- **持久化方案**:
  - 保存 Cookie 到 `crew-hotspot/data/cookies/xiaohongshu.json`
  - 关键 Cookie: `web_session`, `xsecappid`, `a1`, `webId`
- **验证方式**: 访问个人主页,检查是否能看到"发布笔记"按钮

### 2. 微博 (Weibo)
- **登录方式**: 扫码登录 (推荐) / 账号密码
- **Cookie 有效期**: 约 7-15 天
- **持久化方案**:
  - 保存 Cookie 到 `crew-hotspot/data/cookies/weibo.json`
  - 关键 Cookie: `SUB`, `SUBP`, `ALF`, `SSOLoginState`
- **验证方式**: 访问首页,检查是否显示用户名

### 3. 知乎 (Zhihu)
- **登录方式**: 扫码登录 (推荐) / 手机号+验证码
- **Cookie 有效期**: 约 30 天
- **持久化方案**:
  - 保存 Cookie 到 `crew-hotspot/data/cookies/zhihu.json`
  - 关键 Cookie: `z_c0`, `d_c0`, `q_c1`, `_zap`
- **验证方式**: 访问个人主页,检查是否能看到"写文章"按钮

### 4. B站 (Bilibili)
- **登录方式**: 扫码登录 (推荐) / 手机号+验证码
- **Cookie 有效期**: 约 30 天
- **持久化方案**:
  - 保存 Cookie 到 `crew-hotspot/data/cookies/bilibili.json`
  - 关键 Cookie: `SESSDATA`, `bili_jct`, `DedeUserID`, `DedeUserID__ckMd5`
- **验证方式**: 访问个人空间,检查是否能看到"投稿管理"

### 5. 抖音 (Douyin)
- **登录方式**: 扫码登录 (推荐) / 手机号+验证码
- **Cookie 有效期**: 约 7-15 天
- **持久化方案**:
  - 保存 Cookie 到 `crew-hotspot/data/cookies/douyin.json`
  - 关键 Cookie: `sessionid`, `sessionid_ss`, `sid_guard`, `uid_tt`
- **验证方式**: 访问创作者中心,检查是否能看到"发布视频"

---

## 登录流程设计

### 方案 1: Chrome DevTools MCP (推荐)

使用 Chrome DevTools MCP 工具,一次性完成所有平台登录:

```bash
# 1. 启动浏览器会话
# 2. 依次访问各平台登录页
# 3. 你扫码登录
# 4. 自动提取并保存 Cookie
# 5. 验证登录态
```

**优点**:
- 真实浏览器环境,不易被检测
- 支持扫码登录
- Cookie 自动提取
- 可视化操作,你能看到整个过程

**实现**:
```python
# 使用 Chrome MCP 工具
# mcp__chrome-devtools__new_page - 打开登录页
# mcp__chrome-devtools__take_screenshot - 截图二维码给你扫
# mcp__chrome-devtools__wait_for - 等待登录成功
# 提取 Cookie 并保存
```

### 方案 2: 手动导入 Cookie (备选)

如果你已经在浏览器登录过:

```bash
# 使用 /setup-browser-cookies skill
# 从你的真实浏览器 (Chrome/Arc/Brave) 导入 Cookie
```

---

## Cookie 持久化架构

### 目录结构
```
crew-hotspot/
├── data/
│   ├── cookies/
│   │   ├── xiaohongshu.json
│   │   ├── weibo.json
│   │   ├── zhihu.json
│   │   ├── bilibili.json
│   │   └── douyin.json
│   └── cookies/.gitignore  # 防止 Cookie 泄露
```

### Cookie 管理器

```python
# src/crew_hotspot/cookie_manager.py

class CookieManager:
    """Cookie 持久化管理"""

    def save_cookies(self, platform: str, cookies: list):
        """保存 Cookie"""
        filepath = f"data/cookies/{platform}.json"
        with open(filepath, 'w') as f:
            json.dump({
                "platform": platform,
                "cookies": cookies,
                "saved_at": datetime.now().isoformat(),
                "expires_at": self._calculate_expiry(cookies)
            }, f, indent=2)

    def load_cookies(self, platform: str) -> list:
        """加载 Cookie"""
        filepath = f"data/cookies/{platform}.json"
        if not os.path.exists(filepath):
            return []

        with open(filepath) as f:
            data = json.load(f)

        # 检查是否过期
        if self._is_expired(data):
            return []

        return data["cookies"]

    def verify_login(self, platform: str) -> bool:
        """验证登录态是否有效"""
        # 使用 Chrome MCP 访问平台,检查登录状态
        pass

    def refresh_if_needed(self, platform: str):
        """自动刷新即将过期的 Cookie"""
        # 检查过期时间,提前 3 天提醒你重新登录
        pass
```

### 自动加载 Cookie

```python
# src/crew_hotspot/publish_engine.py

class PublishEngine:
    def __init__(self):
        self.cookie_manager = CookieManager()

    async def publish(self, platform: str, content: dict):
        # 1. 加载 Cookie
        cookies = self.cookie_manager.load_cookies(platform)

        # 2. 验证登录态
        if not cookies or not self.cookie_manager.verify_login(platform):
            raise Exception(f"{platform} 未登录或登录已过期,请重新登录")

        # 3. 使用 Chrome MCP 发布
        # 自动注入 Cookie
        # 执行发布操作
        pass
```

---

## 登录态监控

### 定时检查
```python
# src/crew_hotspot/scheduler.py

def schedule_cookie_check():
    """每天检查一次 Cookie 有效性"""
    scheduler.add_job(
        check_all_cookies,
        trigger="cron",
        hour=9,  # 每天早上 9 点检查
        id="cookie_check"
    )

def check_all_cookies():
    """检查所有平台 Cookie"""
    platforms = ["xiaohongshu", "weibo", "zhihu", "bilibili", "douyin"]
    cookie_manager = CookieManager()

    for platform in platforms:
        if not cookie_manager.verify_login(platform):
            # 发送通知 (飞书消息)
            send_notification(f"{platform} 登录已过期,请重新登录")
```

### 过期提醒
```python
def check_expiry_warning():
    """检查即将过期的 Cookie (提前 3 天提醒)"""
    for platform in platforms:
        days_left = cookie_manager.get_days_until_expiry(platform)
        if days_left <= 3:
            send_notification(f"{platform} 登录将在 {days_left} 天后过期")
```

---

## 安全措施

### 1. Cookie 加密存储
```python
from cryptography.fernet import Fernet

class SecureCookieManager(CookieManager):
    def __init__(self):
        # 从环境变量读取加密密钥
        self.key = os.environ.get("COOKIE_ENCRYPTION_KEY")
        self.cipher = Fernet(self.key)

    def save_cookies(self, platform: str, cookies: list):
        # 加密后保存
        encrypted = self.cipher.encrypt(json.dumps(cookies).encode())
        with open(filepath, 'wb') as f:
            f.write(encrypted)

    def load_cookies(self, platform: str) -> list:
        # 解密后返回
        with open(filepath, 'rb') as f:
            encrypted = f.read()
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted)
```

### 2. .gitignore 配置
```gitignore
# data/cookies/.gitignore
*.json
!.gitignore
```

### 3. 环境变量
```bash
# .env
COOKIE_ENCRYPTION_KEY=your-secret-key-here
```

---

## 一次性登录流程

### 步骤 1: 准备工作
```bash
# 创建 Cookie 存储目录
mkdir -p crew-hotspot/data/cookies
echo "*.json" > crew-hotspot/data/cookies/.gitignore
```

### 步骤 2: 批量登录脚本
```python
# scripts/batch_login.py

async def batch_login():
    """批量登录所有平台"""
    platforms = [
        ("xiaohongshu", "https://creator.xiaohongshu.com/login"),
        ("weibo", "https://weibo.com/login.php"),
        ("zhihu", "https://www.zhihu.com/signin"),
        ("bilibili", "https://passport.bilibili.com/login"),
        ("douyin", "https://creator.douyin.com/"),
    ]

    cookie_manager = CookieManager()

    for platform, login_url in platforms:
        print(f"\n{'='*50}")
        print(f"正在登录: {platform}")
        print(f"{'='*50}")

        # 1. 打开登录页
        await chrome_mcp.new_page(login_url)

        # 2. 截图二维码
        screenshot = await chrome_mcp.take_screenshot()
        print(f"请扫描二维码登录 {platform}")
        # 显示二维码给你

        # 3. 等待登录成功 (检测 URL 变化或特定元素)
        await chrome_mcp.wait_for(["个人中心", "发布", "创作"])

        # 4. 提取 Cookie
        cookies = await chrome_mcp.get_cookies()

        # 5. 保存 Cookie
        cookie_manager.save_cookies(platform, cookies)

        # 6. 验证登录
        if cookie_manager.verify_login(platform):
            print(f"✓ {platform} 登录成功")
        else:
            print(f"✗ {platform} 登录失败")

        # 7. 关闭页面
        await chrome_mcp.close_page()

    print("\n所有平台登录完成!")
```

### 步骤 3: 执行登录
```bash
# 我会启动这个脚本
# 你只需要依次扫码 5 个平台
# 每个平台大约 30 秒
# 总共 5 分钟内完成
```

---

## 后续使用

登录完成后,发布内容时会自动:
1. 加载对应平台的 Cookie
2. 验证登录态
3. 如果有效,直接发布
4. 如果失效,通知你重新登录

**你不需要每次都登录,Cookie 会自动管理。**

---

## 推荐方案

**我建议使用方案 1 (Chrome DevTools MCP)**:

1. 我启动批量登录脚本
2. 依次打开 5 个平台登录页
3. 你扫码登录 (每个平台 30 秒)
4. 自动保存 Cookie
5. 以后发布时自动使用,无需再次登录

**优点**:
- 一次性完成所有平台
- Cookie 自动管理
- 过期自动提醒
- 安全加密存储

你确认后我就开始实现这套系统。需要我现在开始吗?
