# Semantic Config Spec V1

## 1. 目标

本文件定义 Data Agent 的数据语义配置层。

这层是整个系统最关键的能力层。因为上传文件分析的真正难点，不是读到文件，而是理解字段、识别口径、处理相似字段、执行业务规则，并把这些解释清楚。

## 2. 为什么必须有语义配置层

仅靠 LLM 和原始字段名做分析，风险很高：

- 字段同名不同义
- 字段近义但不能混用
- 文本字段不规则
- 某些业务规则需要先判断再分析
- 某些筛选条件是隐含知识
- 某些指标不能直接聚合

所以 V1 需要把“业务语义”做成配置。

## 3. 语义配置层的职责

语义配置层至少负责：

1. 字段识别
2. 字段别名映射
3. 字段歧义消解
4. 指标口径定义
5. 默认过滤和排除规则
6. 条件判断规则
7. 问题到分析动作的映射
8. 报告模板需要的数据准备规则
9. 时间区间字段解析

## 4. 推荐模块结构

### 4.1 Field Catalog

记录字段的基础语义。

```json
{
  "field_id": "landing_page_url",
  "display_name": "落地页 URL",
  "aliases": ["lp_url", "landing url"],
  "data_type": "string",
  "semantic_role": "attribute",
  "description": "广告跳转链接地址",
  "example_values": ["https://xxx.com/a", "https://xxx.com/b"],
  "nullable": true
}
```

### 4.2 Alias Mapping

把数据文件中的真实列名映射到标准语义字段。

```json
{
  "candidate_headers": [
    "点位名称",
    "广告位名称",
    "placement_name"
  ],
  "target_field_id": "placement_name",
  "confidence": 0.95
}
```

### 4.3 Ambiguity Rules

定义哪些字段容易混淆、何时必须确认。

```json
{
  "rule_id": "placement_disambiguation",
  "when_headers_present": ["点位类型", "点位名称"],
  "message": "检测到“点位类型”和“点位名称”两个相似字段，请确认本次分析优先使用哪个字段。",
  "options": [
    "优先使用点位类型",
    "优先使用点位名称",
    "两者都使用"
  ]
}
```

### 4.4 Metric Catalog

记录指标定义、计算逻辑和聚合规则。

### 4.5 Business Rules

承载条件判断与过滤逻辑。

### 4.6 Intent Mapping

把用户问题映射为分析意图。

例如：

- 看整体表现
- 看趋势变化
- 看原因
- 生成月报
- 解释字段

## 5. 建议的完整配置结构

```json
{
  "field_catalog": [],
  "alias_mapping_rules": [],
  "ambiguity_rules": [],
  "metric_catalog": [],
  "dimension_catalog": [],
  "time_parsing_rules": [],
  "default_filters": [],
  "exclusion_rules": [],
  "conditional_rules": [],
  "intent_mapping": [],
  "report_data_prep_rules": []
}
```

## 6. V1 重点设计：规则如何表达

你的广告场景里，很多逻辑类似：

- 如果有备注，优先看备注
- 如果 URL 以某些前缀开头，才纳入范围
- 某些字段虽然长得像，但用途不同
- 某些字段缺失时，需要改走备用逻辑

所以规则表达必须足够结构化。

建议至少支持 4 类规则。

### 6.1 默认过滤规则

用于所有分析默认生效。

```json
{
  "rule_id": "exclude_empty_key_fields",
  "type": "default_filter",
  "description": "排除关键字段为空的记录",
  "expression": {
    "operator": "and",
    "conditions": [
      {"field": "date", "op": "not_null"},
      {"field": "campaign_name", "op": "not_null"}
    ]
  }
}
```

### 6.2 排除规则

用于明确不纳入分析范围的数据。

```json
{
  "rule_id": "exclude_internal_urls",
  "type": "exclusion",
  "description": "排除内部测试链接",
  "expression": {
    "field": "landing_page_url",
    "op": "starts_with_any",
    "value": ["https://test.", "https://internal."]
  }
}
```

### 6.3 条件判断规则

用于先判断，再决定使用哪套逻辑。

```json
{
  "rule_id": "remark_priority_rule",
  "type": "conditional",
  "description": "有备注时优先依据备注分类",
  "when": {
    "field": "remark",
    "op": "not_empty"
  },
  "then": {
    "action": "use_field_as_primary_reference",
    "field": "remark"
  },
  "else": {
    "action": "use_default_classification"
  }
}
```

### 6.4 字段优先级规则

用于相似字段并存时的默认策略。

```json
{
  "rule_id": "placement_analysis_preference",
  "type": "field_priority",
  "intent": "placement_breakdown",
  "preferred_fields": ["placement_name", "placement_type"],
  "require_confirmation_if_both_present": true
}
```

## 7. 字段识别流程建议

上传文件后建议走这条链路：

1. 读取表头
2. 做基础类型推断
3. 用别名规则做首轮字段映射
4. 找出未识别字段
5. 找出相似字段冲突
6. 生成字段识别结果
7. 把高风险歧义项交给用户确认

输出最好包含：

- 已识别字段
- 未识别字段
- 候选映射
- 需要确认的字段冲突

## 8. 澄清引擎如何使用语义配置

Clarification Engine 建议至少检查 5 类问题：

1. 缺失关键字段
2. 指标定义缺字段
3. 相似字段冲突
4. 时间范围未明确
5. 分析口径未明确

这部分最好形成标准的“待确认项卡片”，而不是散乱提问。

## 9. Planner 如何使用语义配置

Planner 不是自由发挥，而应该基于语义配置生成计划。

例如用户说：

“帮我看这份广告数据里 3 月的投放表现，并生成月报。”

Planner 需要先读取：

- 哪个字段代表日期
- 哪些字段可以作为月报维度
- 哪些指标是核心指标
- 哪些排除规则默认生效
- 月报模板需要哪些 section

然后再生成计划。

## 10. Executor 如何使用语义配置

Analysis Executor 建议只执行“已明确”的语义。

也就是：

- 已确认字段映射
- 已确认口径
- 已生效过滤规则
- 已确认时间范围

不明确的部分，不应该直接猜测执行。

## 11. 广告数据场景下 V1 应优先支持的字段类别

- 时间字段
- campaign 层字段
- ad group 层字段
- creative 层字段
- placement 层字段
- 曝光、点击、花费、转化类指标字段
- 备注字段
- 落地页 URL 字段
- 渠道 / 媒体字段

## 12. 广告数据场景下 V1 应优先支持的意图类型

- 指标查询
- 趋势分析
- 分维度拆解
- 异常定位
- 生成月报
- 字段解释
- 指标口径解释

## 12.1 广告场景下新增必须支持的规则类型

基于当前 raw data 情况，广告数据智能体还必须额外支持以下规则：

### 费用口径选择规则

费用不能固定绑定单一字段，建议增加标准费用字段 `effective_cost`。

示例：

```json
{
  "rule_id": "effective_cost_rule",
  "type": "derived_metric_source",
  "target_field": "effective_cost",
  "logic": [
    {
      "when": {
        "field": "point_type",
        "op": "equals",
        "value": "百度品专"
      },
      "use_field": "总成本"
    },
    {
      "otherwise": true,
      "use_field": "净总价"
    }
  ]
}
```

### 指标依赖型排除规则

有些记录不是整体删掉，而是只在某些指标计算时排除。

示例：

```json
{
  "rule_id": "exclude_missing_exposure_from_cpm",
  "type": "metric_specific_exclusion",
  "applies_to_metrics": ["cpm"],
  "when": {
    "operator": "and",
    "conditions": [
      {"field": "是否接受DMP曝光监测", "op": "equals", "value": "否"},
      {"field": "effective_cost", "op": "gt", "value": 0}
    ]
  }
}
```

```json
{
  "rule_id": "exclude_missing_click_from_cpc",
  "type": "metric_specific_exclusion",
  "applies_to_metrics": ["cpc"],
  "when": {
    "operator": "and",
    "conditions": [
      {"field": "是否接受DMP点击监测", "op": "equals", "value": "否"},
      {"field": "effective_cost", "op": "gt", "value": 0}
    ]
  }
}
```

### FREE 点位成本排除规则

```json
{
  "rule_id": "exclude_free_from_cost_comparison",
  "type": "metric_specific_exclusion",
  "applies_to_metrics": [
    "high_intent_cost",
    "valid_visitor_cost",
    "cpc",
    "cpm"
  ],
  "when": {
    "field": "广告类型",
    "op": "equals",
    "value": "FREE"
  }
}
```

### URL 前置过滤规则

```json
{
  "rule_id": "ghac_url_prefix_filter",
  "type": "pre_filter",
  "description": "仅分析 GHAC 指定域名落地页",
  "expression": {
    "field": "广告页落地页URL",
    "op": "starts_with",
    "value": "https://www.ghac"
  }
}
```

### 文本字段语义判定规则

`备注` 和 `adslot` 需要支持先做语义分类，再决定是否排除。

建议输出：

- `exclude`
- `include_with_warning`
- `normal`

### 派生指标规则

广告场景中的率和成本类指标，建议全部定义为派生指标，不直接读取源表已有值。

示例：

```json
{
  "metric_id": "ctr",
  "name": "点击率",
  "type": "derived_metric",
  "formula": "CLICK / PV",
  "required_fields": ["CLICK", "PV"],
  "null_strategy": "skip_if_denominator_missing_or_zero"
}
```

```json
{
  "metric_id": "high_intent_cost",
  "name": "高意向访客成本",
  "type": "derived_metric",
  "formula": "effective_cost / 高意向访客",
  "required_fields": ["effective_cost", "高意向访客"],
  "null_strategy": "skip_if_denominator_missing_or_zero"
}
```

### 缺失数据处理规则

广告数据里需要明确区分：

- 值为 0
- 数据缺失
- 不可监测
- 不适用

不能把这些情况都混成 0。

建议增加规则结构：

```json
{
  "rule_id": "untrackable_slot_handling",
  "type": "missing_data_policy",
  "when": {
    "operator": "or",
    "conditions": [
      {"field": "是否接受DMP曝光监测", "op": "equals", "value": "否"},
      {"field": "是否接受DMP点击监测", "op": "equals", "value": "否"}
    ]
  },
  "mark_as": "untrackable",
  "metric_handling": {
    "cpm": "exclude",
    "cpc": "exclude",
    "ctr": "exclude_if_required_fields_missing",
    "arrival_rate": "exclude_if_required_fields_missing",
    "valid_visitor_rate": "exclude_if_required_fields_missing",
    "high_intent_rate": "exclude_if_required_fields_missing",
    "high_intent_cost": "exclude_if_required_fields_missing",
    "valid_visitor_cost": "exclude_if_required_fields_missing"
  }
}
```

### 时间区间解析规则

广告场景中的 `投放时间` 是区间文本，建议单独定义解析规则。

```json
{
  "rule_id": "campaign_date_range_parser",
  "source_field": "投放时间",
  "type": "date_range_parser",
  "pattern": "YYYY-MM-DD至YYYY-MM-DD",
  "outputs": ["start_date", "end_date"],
  "store_original_text": true
}
```

## 13. 数据语义配置的维护方式建议

V1 建议配置以文件方式维护，而不是先进数据库后台。

原因：

- 当前还在方案阶段，频繁迭代会比运营后台更重要
- 先把结构设计对，比做管理界面更关键
- 后续如果验证有效，再做可视化配置台

推荐形式：

- `agent.json`
- `semantic_config.json`
- `report_templates/*.json`

## 14. 当前结论

如果说“智能体定义”决定系统知道自己是谁，那么“数据语义配置层”决定系统到底懂不懂这份数据。

V1 成败很大程度取决于这层设计是否清楚。
