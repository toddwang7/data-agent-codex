# Agent Definition Spec V1

## 1. 目标

本文件定义“分析智能体”的配置结构。

这里的“智能体”不是指一个完全独立的运行时系统，而是指一套可复用的业务分析上下文。系统运行时仍可复用统一的 Planner、Executor、Report Builder，只是根据不同智能体配置切换分析语义与输出规则。

## 2. 设计原则

- 面向业务配置，而不是面向模型 prompt 堆砌
- 可新增多个智能体，但底层执行框架统一
- 能覆盖广告数据场景，也能扩展到其他数据分析场景
- 尽量把“业务解释”“字段规范”“分析边界”“报告模板”结构化

## 3. 一个智能体应该包含什么

V1 建议一个智能体至少由以下 10 类信息组成：

1. 基础信息
2. 数据适用范围
3. 指标与维度定义
4. 字段映射与字段约束
5. 分析规则
6. 派生指标规则
7. 缺失数据处理规则
8. 澄清策略
9. 报告模板
10. 输出风格

## 4. 建议的数据结构

```json
{
  "agent_id": "ad-analysis",
  "name": "广告数据智能体",
  "description": "用于分析广告投放数据，支持问答、趋势分析和月报生成",
  "status": "active",
  "domain": "advertising",
  "supported_file_types": ["csv", "xlsx", "xls"],
  "use_cases": [
    "月报生成",
    "投放效果分析",
    "异常波动定位",
    "自然语言问答"
  ],
  "dataset_profile": {
    "summary": "广告投放明细与聚合数据",
    "expected_granularity": ["day", "campaign", "creative", "placement"],
    "required_minimum_fields": ["date"],
    "recommended_fields": ["impressions", "clicks", "cost", "conversions"]
  },
  "metrics": [],
  "dimensions": [],
  "field_semantics": {},
  "analysis_rules": {},
  "derived_metrics": [],
  "missing_data_policy": {},
  "clarification_policy": {},
  "report_templates": [],
  "response_style": {}
}
```

## 5. 字段拆解

### 5.1 基础信息

- `agent_id`
- `name`
- `description`
- `status`
- `domain`

作用：

- 唯一标识智能体
- 用于展示、切换和后续管理

### 5.2 数据适用范围

- `supported_file_types`
- `dataset_profile.summary`
- `dataset_profile.expected_granularity`
- `dataset_profile.required_minimum_fields`
- `dataset_profile.recommended_fields`

作用：

- 告诉系统这个智能体能处理什么类型的数据
- 在上传后做基础校验
- 在字段不足时触发提醒

### 5.3 指标定义

建议每个指标采用统一结构：

```json
{
  "metric_id": "ctr",
  "name": "点击率",
  "aliases": ["CTR", "click through rate"],
  "definition": "点击数 / 展现数",
  "formula": "clicks / impressions",
  "required_fields": ["clicks", "impressions"],
  "format": "percentage",
  "aggregation_rule": "recalculate",
  "notes": ["不能直接对明细 CTR 求平均"]
}
```

关键点：

- 指标不是只给模型看的说明文案，而是分析执行器会真正依赖的数据定义
- `aggregation_rule` 要单独写明，否则汇总时容易算错

### 5.4 维度定义

```json
{
  "dimension_id": "placement_name",
  "name": "点位名称",
  "aliases": ["广告位名称", "placement"],
  "definition": "广告实际投放位置名称",
  "value_type": "string",
  "groupable": true
}
```

关键点：

- 明确它是否可分组、是否可过滤、是否可用于时间序列
- 相似字段要能区分

### 5.5 字段语义与映射

这是广告场景最关键的一层。

```json
{
  "placement_type": {
    "display_name": "点位类型",
    "aliases": ["版位类型", "资源位类型"],
    "semantic_role": "dimension",
    "value_type": "string",
    "similar_fields": ["placement_name"],
    "disambiguation_hint": "用于区分投放位类别，不代表具体点位名称"
  }
}
```

建议每个字段都支持：

- 展示名
- 同义别名
- 字段角色
- 值类型
- 相似字段
- 字段选择提示
- 示例值

### 5.6 分析规则

这个模块承载你说的“很多要求”。

建议拆成 5 类规则：

- 默认过滤规则
- 排除规则
- 字段优先级规则
- 条件判断规则
- 分析关注重点

示例：

```json
{
  "default_filters": [
    {
      "id": "exclude_empty_date",
      "description": "排除日期为空的数据",
      "expression": "date is not null"
    }
  ],
  "conditional_rules": [
    {
      "id": "remark_priority",
      "description": "若备注存在，优先参考备注判断分类",
      "when": "remark is not empty",
      "then": "use remark as first reference"
    }
  ],
  "field_priority_rules": [
    {
      "question_intent": "placement analysis",
      "preferred_fields": ["placement_name", "placement_type"]
    }
  ]
}
```

### 5.7 派生指标规则

像点击率、到达率、各类成本，不应直接依赖源表已有值，而应定义为分析阶段重算的派生指标。

```json
{
  "metric_id": "high_intent_cost",
  "name": "高意向访客成本",
  "formula": "effective_cost / high_intent_visitors",
  "required_fields": ["effective_cost", "high_intent_visitors"],
  "null_strategy": "skip_if_denominator_missing_or_zero"
}
```

### 5.8 缺失数据处理规则

需要明确区分：

- 真正的 0
- 缺失值
- 不可监测
- 不适用

这些状态不能被混成同一种值。

```json
{
  "mark_untrackable_when": [
    {"field": "accept_dmp_exposure", "op": "equals", "value": "否"},
    {"field": "accept_dmp_click", "op": "equals", "value": "否"}
  ],
  "metric_handling": {
    "cpm": "exclude_if_untrackable_or_missing",
    "cpc": "exclude_if_untrackable_or_missing",
    "ctr": "exclude_if_required_fields_missing",
    "arrival_rate": "exclude_if_required_fields_missing",
    "valid_visitor_rate": "exclude_if_required_fields_missing",
    "high_intent_rate": "exclude_if_required_fields_missing",
    "high_intent_cost": "exclude_if_required_fields_missing",
    "valid_visitor_cost": "exclude_if_required_fields_missing"
  }
}
```

### 5.9 澄清策略

澄清不是补充功能，而是主流程。

```json
{
  "required_before_execution": [
    "time_range",
    "metric_definition",
    "selected_dataset"
  ],
  "ambiguity_checks": [
    {
      "type": "similar_fields",
      "fields": ["placement_type", "placement_name"],
      "ask_user": true
    }
  ],
  "confirmation_style": "button_first"
}
```

### 5.10 报告模板

同一个智能体可能有多个模板：

- 月报
- 周报
- 异常分析
- 自定义问答结果摘要

```json
{
  "template_id": "monthly-report",
  "name": "月报",
  "scenario": "monthly_summary",
  "required_inputs": ["time_range"],
  "sections": [
    "整体表现",
    "趋势变化",
    "核心维度拆解",
    "异常与原因",
    "后续建议"
  ]
}
```

## 6. 新建智能体时前端应该收集哪些内容

V1 不建议让用户一口气填完整套复杂配置。建议分两层：

### 6.1 创建时必填

- 智能体名称
- 场景描述
- 适用数据类型
- 常见分析目标
- 是否包含固定报告模板

### 6.2 创建后完善

- 核心指标定义
- 核心维度定义
- 字段别名映射
- 过滤和排除规则
- 派生指标规则
- 缺失数据处理规则
- 澄清规则
- 模板规则

这样用户不会在创建第一步就被表单吓退。

## 6.3 以后平台上新建其他智能体，能否达到同样效果

可以，但前提是平台配置能力不能只停留在：

- 一个名字
- 一段描述
- 一段 prompt

如果只是这种轻量配置，效果达不到广告数据场景现在要求的深度。

要达到接近同等效果，平台至少要支持这些结构化配置：

- 字段字典
- 字段别名映射
- 指标定义与公式
- 派生指标规则
- 默认过滤规则
- 指标级排除规则
- 缺失数据处理规则
- 文本字段语义分类规则
- 澄清问题模板
- 报告模板

结论：

- 如果平台支持结构化业务配置，后续新建别的智能体可以达到相近效果
- 如果平台只支持写说明文本或 prompt，很难达到同等稳定性和准确度

## 7. 对广告数据智能体的具体建议

第一版可以把“广告数据智能体”预置成系统模板，而不是让用户完全从零创建。

预置模板至少应包含：

- 常见广告指标
- 常见时间维度
- campaign / ad group / creative / placement 等层级字段定义
- 点击、展现、花费、转化等标准指标
- 点位类型 vs 点位名称这类常见歧义字段说明
- 月报模板

## 8. 与系统模块的关系

- Agent Registry 负责读写该配置
- Clarification Engine 读取字段歧义和必确认项
- Planner 读取 use case、指标定义、模板规则
- Analysis Executor 读取指标公式、字段映射、过滤规则
- Report Builder 读取报告模板和输出风格

## 9. V1 不建议做的事

- 不要把整个智能体能力只写成一段超长 system prompt
- 不要把字段说明完全放在自由文本里
- 不要让每个智能体拥有完全不同的运行流程

这些做法短期快，后面会非常难维护。

## 10. 当前结论

V1 的“智能体”本质上应被实现为一份结构化业务分析配置，而不是一套完全独立的 agent runtime。
