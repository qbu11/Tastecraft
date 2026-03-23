# 图片生成系统使用指南

## 概述

全媒体自动营销系统现已集成智能图片生成功能，支持为 5 个主流平台自动生成适配的配图：
- 小红书 (Xiaohongshu)
- 微博 (Weibo)
- 知乎 (Zhihu)
- B站 (Bilibili)
- 抖音 (Douyin)

## 核心特性

### 1. 平台自动适配
- **尺寸适配**: 自动根据平台要求调整图片尺寸
- **风格适配**: 字体大小、布局密度自动优化
- **比例适配**: 支持 1:1、3:4、9:16、16:9 等多种比例

### 2. 多种配色方案
- **tech**: 科技蓝紫系 (适合 AI/科技主题)
- **business**: 商务蓝白系 (适合企业/专业主题)
- **vibrant**: 活力橙黄系 (适合创意/生活主题)
- **minimal**: 极简灰白系 (适合简约风格)

### 3. 四种图片类型
- **封面图 (Cover)**: 主视觉，吸引点击
- **信息图 (Comparison)**: 数据对比表格
- **卡片图 (Highlights)**: 要点列举，功能介绍
- **总结图 (Summary)**: 结论建议，行动指南

---

## API 使用

### 启动服务

```bash
cd crew-hotspot
python api.py
```

服务地址: `http://localhost:8100`
API 文档: `http://localhost:8100/docs`

---

### 1. 生成全套配图

**接口**: `POST /api/images/generate`

**请求示例**:

```bash
curl -X POST "http://localhost:8100/api/images/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xiaohongshu",
    "color_scheme": "tech",
    "content": {
      "title": "AI三巨头激战2026!",
      "subtitle": "Claude Opus 4.6 登顶排行榜",
      "tags": ["AI", "科技", "Claude"],
      "comparison": {
        "title": "三巨头性能对比",
        "headers": ["指标", "Claude", "GPT-5.2", "Gemini"],
        "rows": [
          ["上下文", "100万⭐", "20万", "200万"],
          ["SWE-bench", "80.8%⭐", "73.2%", "75.6%"],
          ["编程能力", "⭐⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐"]
        ],
        "highlight_col": 1
      },
      "highlights": {
        "title": "Claude Opus 4.6 三大亮点",
        "items": [
          {
            "title": "100万token上下文窗口",
            "desc1": "相当于3本《三体》",
            "desc2": "是GPT-5.2的5倍"
          },
          {
            "title": "Agent Teams多智能体",
            "desc1": "多个AI协同工作",
            "desc2": "就像组了个超强战队"
          },
          {
            "title": "编程能力爆表",
            "desc1": "SWE-bench 80.8%",
            "desc2": "完爆竞争对手"
          }
        ]
      },
      "recommendations": {
        "title": "我的选择建议",
        "items": [
          ["写代码", "Claude Opus 4.6", "编程能力最强"],
          ["日常聊天", "GPT-5.2", "响应快，生态好"],
          ["多模态任务", "Gemini 3.1 Pro", "原生多模态"],
          ["中文场景", "Kimi K2 / GLM-5", "中文优化"]
        ],
        "slogan": "2026年AI大爆发"
      }
    }
  }'
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "platform": "xiaohongshu",
    "color_scheme": "tech",
    "output_dir": "generated_images/xiaohongshu/20260323_200730",
    "images": [
      "generated_images/xiaohongshu/20260323_200730/1_cover.png",
      "generated_images/xiaohongshu/20260323_200730/2_comparison.png",
      "generated_images/xiaohongshu/20260323_200730/3_highlights.png",
      "generated_images/xiaohongshu/20260323_200730/4_recommendations.png"
    ],
    "count": 4
  }
}
```

---

### 2. 生成单张图片

**接口**: `POST /api/images/generate-single`

**封面图示例**:

```bash
curl -X POST "http://localhost:8100/api/images/generate-single" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "weibo",
    "color_scheme": "vibrant",
    "image_type": "cover",
    "data": {
      "title": "AI大爆发时代来临",
      "subtitle": "2026年最值得关注的技术趋势",
      "tags": ["AI", "科技", "趋势"],
      "style": "gradient"
    }
  }'
```

**对比表格示例**:

```bash
curl -X POST "http://localhost:8100/api/images/generate-single" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "zhihu",
    "color_scheme": "business",
    "image_type": "comparison",
    "data": {
      "title": "主流AI模型对比",
      "headers": ["模型", "参数量", "价格", "速度"],
      "rows": [
        ["Claude Opus 4.6", "未公开", "$5/$25", "快"],
        ["GPT-5.2", "1.8T", "$3/$15", "中"],
        ["Gemini 3.1 Pro", "未公开", "$2/$10", "快"]
      ],
      "highlight_col": 0
    }
  }'
```

---

### 3. 查询平台配置

**接口**: `GET /api/images/platforms`

```bash
curl "http://localhost:8100/api/images/platforms"
```

**响应**:

```json
{
  "success": true,
  "data": {
    "xiaohongshu": {
      "name": "小红书",
      "cover_size": [1080, 1080],
      "info_size": [1080, 1080],
      "card_size": [1080, 1080],
      "font_scale": 1.0
    },
    "weibo": {
      "name": "微博",
      "cover_size": [1080, 1080],
      "info_size": [1080, 1080],
      "card_size": [1080, 1080],
      "font_scale": 0.9
    },
    "zhihu": {
      "name": "知乎",
      "cover_size": [1120, 630],
      "info_size": [1080, 800],
      "card_size": [1080, 720],
      "font_scale": 0.8
    },
    "bilibili": {
      "name": "B站",
      "cover_size": [1920, 1080],
      "info_size": [1080, 1440],
      "card_size": [1080, 1440],
      "font_scale": 0.9
    },
    "douyin": {
      "name": "抖音",
      "cover_size": [1080, 1920],
      "info_size": [1080, 1920],
      "card_size": [1080, 1920],
      "font_scale": 1.2
    }
  }
}
```

---

### 4. 查询配色方案

**接口**: `GET /api/images/color-schemes`

```bash
curl "http://localhost:8100/api/images/color-schemes"
```

---

### 5. 查看生成历史

**接口**: `GET /api/images/history`

```bash
# 查看所有平台
curl "http://localhost:8100/api/images/history?limit=20"

# 查看指定平台
curl "http://localhost:8100/api/images/history?platform=xiaohongshu&limit=10"
```

---

## Python SDK 使用

### 基础用法

```python
from src.crew_hotspot.image_generator import ImageGenerator

# 创建生成器
generator = ImageGenerator(
    platform="xiaohongshu",
    color_scheme="tech"
)

# 生成封面图
cover = generator.generate_cover(
    title="AI三巨头激战2026!",
    subtitle="Claude Opus 4.6 登顶排行榜",
    tags=["AI", "科技", "Claude"],
    style="gradient"
)
cover.save("cover.png")

# 生成对比表格
comparison = generator.generate_comparison(
    title="三巨头性能对比",
    headers=["指标", "Claude", "GPT-5.2", "Gemini"],
    rows=[
        ["上下文", "100万", "20万", "200万"],
        ["SWE-bench", "80.8%", "73.2%", "75.6%"]
    ],
    highlight_col=1
)
comparison.save("comparison.png")

# 生成亮点卡片
highlights = generator.generate_highlights(
    title="核心亮点",
    highlights=[
        {
            "title": "100万token上下文",
            "desc1": "相当于3本《三体》",
            "desc2": "是GPT的5倍"
        }
    ]
)
highlights.save("highlights.png")

# 生成总结建议
summary = generator.generate_summary(
    title="我的建议",
    recommendations=[
        ("写代码", "Claude Opus 4.6", "编程能力最强"),
        ("日常聊天", "GPT-5.2", "响应快")
    ],
    slogan="2026年AI大爆发"
)
summary.save("summary.png")
```

### 批量生成

```python
from src.crew_hotspot.image_generator import generate_for_platform

# 定义内容
content = {
    "title": "AI三巨头激战2026!",
    "subtitle": "Claude Opus 4.6 登顶排行榜",
    "tags": ["AI", "科技"],
    "comparison": {...},
    "highlights": {...},
    "recommendations": {...}
}

# 为所有平台生成
platforms = ["xiaohongshu", "weibo", "zhihu", "bilibili", "douyin"]

for platform in platforms:
    paths = generate_for_platform(
        platform=platform,
        content=content,
        output_dir=f"output/{platform}",
        color_scheme="tech"
    )
    print(f"{platform}: 生成了 {len(paths)} 张图片")
```

---

## 集成到发布流程

### 1. 内容生成 + 图片生成

```python
from src.crew_hotspot.crews.content_crew import ContentCrew
from src.crew_hotspot.image_generator import generate_for_platform

# 1. 生成内容
crew = ContentCrew()
result = crew.run(
    topic="AI技术突破",
    platform="xiaohongshu"
)

# 2. 提取内容结构
content_data = {
    "title": result["title"],
    "subtitle": result.get("subtitle"),
    "tags": result.get("tags", []),
    # ... 其他字段
}

# 3. 生成配图
image_paths = generate_for_platform(
    platform="xiaohongshu",
    content=content_data,
    output_dir="drafts/images",
    color_scheme="tech"
)

# 4. 保存到草稿
draft = {
    "content": result["content"],
    "images": image_paths,
    "platform": "xiaohongshu"
}
```

### 2. 自动发布流程

```python
from src.crew_hotspot.publish_engine import PublishEngine

# 创建发布引擎
engine = PublishEngine()

# 发布到草稿箱
result = engine.publish_to_draft(
    platform="xiaohongshu",
    content={
        "title": "AI三巨头激战2026!",
        "body": "...",
        "images": [
            "generated_images/xiaohongshu/20260323/1_cover.png",
            "generated_images/xiaohongshu/20260323/2_comparison.png",
            "generated_images/xiaohongshu/20260323/3_highlights.png"
        ],
        "tags": ["AI", "科技"]
    }
)
```

---

## 最佳实践

### 1. 平台选择建议

| 平台 | 推荐图片类型 | 推荐数量 | 配色方案 |
|------|-------------|---------|---------|
| 小红书 | 封面 + 信息图 + 卡片 | 3-6张 | tech / vibrant |
| 微博 | 封面 + 九宫格 | 1或9张 | vibrant / business |
| 知乎 | 封面 + 信息图 + 架构图 | 5-10张 | business / minimal |
| B站 | 封面 + 截图 + 对比图 | 3-5张 | tech / vibrant |
| 抖音 | 竖屏封面 + 卡片滑动 | 3-8张 | vibrant / tech |

### 2. 内容结构建议

```python
# 完整的内容结构
content = {
    # 必填
    "title": "主标题 (20-30字)",

    # 可选
    "subtitle": "副标题 (10-20字)",
    "tags": ["标签1", "标签2", "标签3"],

    # 对比表格 (可选)
    "comparison": {
        "title": "表格标题",
        "headers": ["列1", "列2", "列3"],
        "rows": [
            ["数据1", "数据2", "数据3"],
            ["数据4", "数据5", "数据6"]
        ],
        "highlight_col": 1  # 高亮第2列
    },

    # 亮点卡片 (可选)
    "highlights": {
        "title": "亮点标题",
        "items": [
            {
                "title": "亮点1标题",
                "desc1": "描述1",
                "desc2": "描述2"
            }
        ]
    },

    # 总结建议 (可选)
    "recommendations": {
        "title": "建议标题",
        "items": [
            ("场景1", "推荐方案1", "原因1"),
            ("场景2", "推荐方案2", "原因2")
        ],
        "slogan": "底部标语"
    }
}
```

### 3. 性能优化

```python
# 1. 字体缓存 - 自动处理，无需手动管理

# 2. 批量生成 - 使用 generate_all_for_content
generator = ImageGenerator("xiaohongshu", "tech")
paths = generator.generate_all_for_content(content, "output_dir")

# 3. 异步生成 (如需要)
import asyncio

async def generate_async(platform, content):
    return await asyncio.to_thread(
        generate_for_platform,
        platform, content, f"output/{platform}"
    )

# 并行生成多个平台
results = await asyncio.gather(
    generate_async("xiaohongshu", content),
    generate_async("weibo", content),
    generate_async("zhihu", content)
)
```

---

## 故障排查

### 1. 字体问题

**问题**: 中文显示为方块或乱码

**解决**:
```python
# 检查字体路径
from src.crew_hotspot.image_generator import FontManager

for path in FontManager.FONT_PATHS_CN:
    print(f"{path}: {'存在' if os.path.exists(path) else '不存在'}")

# Windows: 确保安装了微软雅黑
# macOS: 确保安装了苹方
# Linux: 安装 wqy-microhei
```

### 2. 图片尺寸问题

**问题**: 生成的图片尺寸不符合预期

**解决**:
```python
# 检查平台配置
from src.crew_hotspot.image_generator import PLATFORM_CONFIGS, Platform

config = PLATFORM_CONFIGS[Platform.XIAOHONGSHU]
print(f"封面尺寸: {config.cover_size}")
print(f"信息图尺寸: {config.info_size}")
```

### 3. 内存问题

**问题**: 生成大量图片时内存占用过高

**解决**:
```python
# 分批生成
import gc

for i, platform in enumerate(platforms):
    generate_for_platform(platform, content, f"output/{platform}")

    # 每生成一个平台后清理内存
    if i % 2 == 0:
        gc.collect()
```

---

## 更新日志

### v1.0.0 (2026-03-23)
- ✅ 支持 5 个主流平台
- ✅ 4 种配色方案
- ✅ 4 种图片类型
- ✅ 平台自动适配
- ✅ API 接口集成
- ✅ Python SDK

---

## 下一步计划

- [ ] 支持自定义字体
- [ ] 支持图片模板库
- [ ] 支持 AI 图片生成 (DALL-E / Midjourney)
- [ ] 支持图片后处理 (滤镜、水印)
- [ ] 支持视频封面生成
- [ ] 支持 GIF 动图生成

---

_最后更新: 2026-03-23_
