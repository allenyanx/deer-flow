# SOUL.md 模板系统使用指南

## 📋 概述

SOUL.md 模板系统是 DeerTeamX 的核心功能之一，通过**模板化生成 + 自定义覆盖**的双层策略，平衡易用性和灵活性，确保生成的 System Prompt 质量。

### 核心特性

- ✅ **6种预设模板**：覆盖常见角色类型（分析师、开发者、创作者等）
- ✅ **智能自动选择**：基于角色特征自动匹配最合适的模板
- ✅ **动态内容追加**：自动添加 Skills、Tools、Delegation、Model 配置章节
- ✅ **高级模式支持**：允许用户直接编辑完整的 Markdown 格式 System Prompt
- ✅ **API 预览功能**：实时预览生成的 SOUL.md 内容

---

## 🎯 快速开始

### 1. 基本用法

```python
from deerteamx.services.team_service import TeamService

# 定义角色配置
role = {
    "name": "Data Analyst",
    "goal": "Analyze Q1 sales data and identify trends",
    "backstory": "You are a senior data scientist with 10+ years of experience.",
    "skills": ["data-analysis", "chart-visualization"],
    "model": "gpt-4"
}

# 生成 SOUL.md（自动选择模板）
soul_content = TeamService.generate_soul_content(role)
print(soul_content)
```

**输出示例**：
```markdown
# Expert Analyst: Data Analyst

## Professional Background
You are a senior data scientist with 10+ years of experience.

## Mission Statement
Analyze Q1 sales data and identify trends

## Analytical Framework
1. **Problem Decomposition**: Break down complex problems...
...

## Available Skills
You have access to the following specialized skills:

- `data-analysis`
- `chart-visualization`

Use these skills when they can help you accomplish your goals more effectively.

## Technical Configuration
- **LLM Model**: `gpt-4`
- Optimize your approach based on this model's strengths and limitations
```

---

### 2. 指定模板

```python
# 显式指定使用创意创作型模板
soul_content = TeamService.generate_soul_content(
    role,
    template_name="creative_creator"
)
```

---

### 3. 自定义内容优先

```python
# 如果提供了 soul_content，将直接使用（忽略模板）
role = {
    "name": "Custom Role",
    "soul_content": "# My Custom Prompt\n\nThis is my complete system prompt..."
}

soul_content = TeamService.generate_soul_content(role)
# 输出就是用户提供的完整内容
```

---

## 📚 预设模板库

| 模板 ID | 名称 | 适用场景 | 特点 |
|---------|------|---------|------|
| `default` | 📋 通用标准 | 大多数常规角色 | 平衡简洁性和完整性 |
| `expert_analyst` | 🔬 专家分析型 | 数据分析师、研究员、审计员 | 强调方法论、证据链、批判性思维 |
| `creative_creator` | 🎨 创意创作型 | 文案撰写、内容创作、营销策划 | 鼓励创新、多样化视角、情感共鸣 |
| `technical_developer` | 💻 技术开发型 | 程序员、架构师、DevOps 工程师 | 强调代码质量、最佳实践、安全性 |
| `coordinator_manager` | 👥 协调管理型 | 项目经理、团队领导、流程协调者 | 强调沟通、协作、资源调配 |
| `quality_assurance` | ✅ 质量控制型 | 测试工程师、审核员、合规检查员 | 强调细致、标准、系统性 |

---

## 🤖 自动选择算法

当不指定模板时，系统会基于角色特征（name/goal/backstory）进行智能匹配：

### 关键词映射表

| 模板 | 关键词示例 |
|------|-----------|
| `expert_analyst` | 分析、analyze、research、研究、audit、审计、data、统计 |
| `creative_creator` | 创作、create、write、撰写、design、设计、content、文案 |
| `technical_developer` | 开发、develop、code、代码、program、编程、engineer、工程 |
| `coordinator_manager` | 管理、manage、coordinate、协调、lead、领导、project、项目 |
| `quality_assurance` | 测试、test、qa、quality、质量、review、审查、verify、验证 |

### 匹配逻辑

```python
# 1. 提取文本特征（转为小写）
text_features = f"{name} {goal} {backstory}".lower()

# 2. 计算每个模板的匹配得分
scores = {}
for template_id, keywords in keyword_mapping.items():
    score = sum(1 for keyword in keywords if keyword in text_features)
    scores[template_id] = score

# 3. 选择最高分的模板（若平局则返回 default）
best_template = max(scores, key=scores.get)
```

---

## 🔌 API 接口

### 获取可用模板列表

**端点**: `GET /api/v1/soul/templates`

**响应**:
```json
{
  "data": {
    "templates": [
      {
        "id": "auto",
        "name": "🤖 自动选择（推荐）",
        "description": "系统根据角色特征智能匹配最合适的模板",
        "icon": "robot"
      },
      {
        "id": "default",
        "name": "📋 通用标准",
        "description": "适用于大多数常规角色，平衡简洁性和完整性",
        "icon": "file-text"
      }
      // ... 其他模板
    ]
  }
}
```

---

### 预览生成的 SOUL.md

**端点**: `POST /api/v1/soul/preview`

**请求体**:
```json
{
  "name": "Data Analyst",
  "goal": "Analyze Q1 sales data and identify trends",
  "backstory": "You are a senior data scientist...",
  "skills": ["data-analysis", "chart-visualization"],
  "model": "gpt-4-turbo",
  "soul_template": "expert_analyst",
  "allow_delegation": false,
  "tool_groups": ["bash", "file_read"]
}
```

**响应**:
```json
{
  "data": {
    "soul_content": "# Expert Analyst: Data Analyst\n\n## Professional Background\n..."
  }
}
```

**注意**: 此接口仅用于预览，不会保存到数据库。

---

## 🏗️ 架构集成

### StaticTeamGraph Builder 集成

在团队执行时，`StaticTeamGraphBuilder._ensure_custom_agent_exists()` 会自动调用 SOUL.md 生成逻辑：

```python
async def _ensure_custom_agent_exists(self, agent_name: str, role: dict):
    # 1. 检查 Agent 是否存在
    # 2. 不存在则创建（包含生成的 SOUL.md）
    # 3. 已存在则更新 SOUL.md
    # 4. 原子性更新 Skills
    
    soul_content = self._generate_soul_for_role(role)
    
    # 通过 Gateway API 同步到 DeerFlow
    await client.post("/api/agents", json={
        "name": agent_name,
        "soul": soul_content,
        ...
    })
```

### 生成流程

```mermaid
graph LR
    A[用户输入<br>结构化字段] --> B{是否有<br>soul_content?}
    B -->|有| C[直接使用自定义内容]
    B -->|无| D{指定了<br>soul_template?}
    D -->|是| E[使用指定模板]
    D -->|否| F[自动选择模板]
    E --> G[渲染模板]
    F --> G
    C --> H[保存到 config_snapshot]
    G --> H
    H --> I[同步到 DeerFlow Gateway]
    I --> J[写入 agents/{name}/SOUL.md]
```

---

## 📊 性能优化

### 客户端缓存

前端对相同的角色配置组合进行本地缓存（TTL: 5分钟）：

```typescript
const cacheKey = `soul_preview_${md5(`${name}${goal}${backstory}${template}`)}`;
const cached = localStorage.getItem(cacheKey);

if (cached && Date.now() - JSON.parse(cached).timestamp < 5 * 60 * 1000) {
  return JSON.parse(cached).content;
}
```

### 服务端缓存（待实现）

Redis 缓存热点角色的生成结果（TTL: 1小时）：

```python
cache_key = f"soul_preview:{hashlib.md5(config_json.encode()).hexdigest()}"
cached = await redis.get(cache_key)
```

---

## 🧪 测试

运行单元测试：

```bash
cd /home/ycp/workSpace/ai/games_dev/deer-flow/backend
pytest tests/test_soul_templates.py -v
```

**测试覆盖**：
- ✅ 模板库功能（列出、获取、渲染）
- ✅ 自动选择算法（6种角色类型）
- ✅ SOUL.md 生成逻辑（自定义、指定模板、自动选择）
- ✅ 动态章节追加（Skills、Tools、Delegation、Model）
- ✅ 边界情况处理（空角色、无效模板）

---

## 📝 最佳实践

### 1. 优先使用自动选择

让系统智能匹配模板，通常能获得较好的效果：

```python
# ✅ 推荐
soul_content = TeamService.generate_soul_content(role)

# ❌ 不推荐（除非有特殊需求）
soul_content = TeamService.generate_soul_content(role, template_name="expert_analyst")
```

### 2. 控制 SOUL.md 长度

建议控制在 2000-5000 字符以内，避免 Token 消耗过大：

```python
soul_content = TeamService.generate_soul_content(role)
if len(soul_content) > 5000:
    logger.warning(f"SOUL.md too long: {len(soul_content)} chars")
```

### 3. 语言一致性

SOUL.md 的语言应与任务输入语言保持一致：

```python
# ✅ 中文任务用中文 Prompt
role = {
    "name": "数据分析师",
    "goal": "分析销售数据并识别趋势",
    "backstory": "你是一位资深数据科学家..."
}

# ✅ 英文任务用英文 Prompt
role = {
    "name": "Data Analyst",
    "goal": "Analyze sales data and identify trends",
    "backstory": "You are a senior data scientist..."
}
```

### 4. 定期观察执行日志

查看 Agent 是否按预期行为执行，必要时调整模板或自定义内容：

```python
logger.info(f"Generated SOUL.md for '{role.get('name')}' ({len(soul_content)} chars)")
```

---

## 🔮 未来演进

### V1.1 规划

- [ ] **语义相似度匹配**：使用 Embedding 替代关键词匹配
- [ ] **分屏预览**：左侧编辑，右侧实时渲染 Markdown
- [ ] **版本对比**：查看编辑前后的 Diff
- [ ] **AI 优化建议**：调用 LLM 优化 Prompt 质量
- [ ] **增量更新**：支持部分章节重新渲染

### V2.0 规划

- [ ] **模板市场**：用户可分享和订阅社区模板
- [ ] **多语言支持**：同一模板支持中英文双语生成
- [ ] **A/B 测试框架**：自动测试不同模板的效果并推荐最优解
- [ ] **Prompt 质量评分**：基于历史执行数据评估 Prompt 质量

---

## 📖 相关文档

- [SOUL_TEMPLATE_ARCHITECTURE.md](../../docs/deer-teamx-docs/SOUL_TEMPLATE_ARCHITECTURE.md) - 完整架构设计
- [API_REFERENCE.md](../../docs/deer-teamx-docs/API_REFERENCE.md#8-soulmd-模板-api) - API 接口文档
- [Per-Role Custom Agent 隔离架构.md](../../docs/deer-teamx-docs/dev_docs/Per-Role%20Custom%20Agent%20隔离架构.md) - Agent 隔离方案

---

## 🛠️ 文件位置

```
backend/deerteamx/
├── graph/
│   ├── soul_templates.py          # 模板定义与渲染引擎
│   └── soul_auto_selector.py      # 自动选择算法
├── services/
│   └── team_service.py            # SOUL.md 生成逻辑（generate_soul_content）
├── api/routers/
│   └── soul.py                    # API 路由（/soul/templates, /soul/preview）
└── main.py                        # 路由注册

backend/tests/
└── test_soul_templates.py         # 单元测试
```
