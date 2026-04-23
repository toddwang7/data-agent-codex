# Config Schema Guide

## 1. 目的

这一组 Schema 文件定义了平台配置格式，而不是业务内容本身。

可以把它理解成：

- `agent.json` 是某个智能体的配置内容
- `agent.schema.json` 是“这个文件应该怎么填”的规则

同理：

- `semantic-config.json` 对应 `semantic-config.schema.json`
- 报告模板 JSON 对应 `report-template.schema.json`

## 2. 当前新增的 Schema 文件

- `config/schemas/common.schema.json`
- `config/schemas/agent.schema.json`
- `config/schemas/semantic-config.schema.json`
- `config/schemas/report-template.schema.json`

## 3. 这套 Schema 解决什么问题

### 3.1 统一平台配置格式

后面无论是广告数据智能体，还是其他新的数据智能体，平台都可以按同一套结构去收配置。

### 3.2 让配置可校验

Schema 可以规定：

- 哪些字段必填
- 哪些字段是什么类型
- 哪些字段只能填固定选项
- 哪些嵌套结构必须存在

### 3.3 让前后端有共同标准

前端知道该收什么配置。

后端知道该怎么读这些配置。

## 4. 当前三类主配置

### 4.1 Agent Schema

定义智能体本身：

- 名称
- 描述
- 支持的文件类型
- 能力列表
- 默认流程
- 澄清策略
- 模板引用

### 4.2 Semantic Config Schema

定义数据语义和分析规则：

- 字段字典
- 表头映射
- 歧义规则
- 时间区间解析规则
- 报告月份解析规则
- 指标定义
- 默认过滤规则
- 指标级排除规则
- 缺失数据策略
- 文本语义规则
- 澄清卡片和澄清流程

### 4.3 Report Template Schema

定义报告模板：

- 模板 id
- 适用场景
- 适用月份数量条件
- 必须确认项
- 报告 section

## 5. 为什么先做 Schema 是对的

因为现在最容易失控的不是模型能力，而是配置结构。

如果不先把格式定清楚，后面：

- 平台页面很难做
- 配置很容易越来越乱
- 不同智能体会长得不一样
- 后端执行逻辑会很难维护

## 6. 当前状态

这一步已经把“广告数据智能体”的配置，从文档草案推进到了“有正式格式约束”的阶段。

下一步最自然的工作就是：

1. 用 Schema 继续完善广告智能体配置
2. 实现配置校验
3. 开始搭上传和澄清流程
