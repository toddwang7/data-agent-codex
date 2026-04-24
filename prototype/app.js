const defaultMessages = [];
const APP_VERSION = "v0.7.0";

const DEFAULT_LOCAL_API_BASE = "http://127.0.0.1:8765";

function getApiBase() {
  if (window.location.protocol === "file:") {
    return DEFAULT_LOCAL_API_BASE;
  }
  return "";
}

function apiUrl(path) {
  return `${getApiBase()}${path}`;
}

const defaultReportSections = [
  {
    eyebrow: "Header",
    title: "报告头部",
    text: "当前是广告投放月报的预览态，上传数据、确认口径和特殊样本处理后，右侧会继续沉淀成正式报告内容。",
    metrics: ["结构化月报", "支持追问优化"],
    bullets: [
      "这里承接标题、时间范围、数据范围和计算说明",
      "后续可继续在对话里要求补充更正式的汇报表达"
    ]
  },
  {
    eyebrow: "Overview",
    title: "整体情况",
    text: "1 月高意向访客成本为 499.62，2 月降至 368.50。当前预览结果显示 2 月效率改善明显，但仍需要先确认报告月份、特殊样本和费用口径。",
    metrics: ["2025-01 高意向成本 499.62", "2025-02 高意向成本 368.50"],
    bullets: [
      "当前以重算后的成本和链路指标为准",
      "不直接采用源表现成 CTR、成本列",
      "跨月趋势先看整体，再拆到车型和媒体"
    ]
  },
  {
    eyebrow: "Trend",
    title: "媒体趋势",
    text: "当前执行预览中，悠易互通、抖音、今日头条、汽车之家构成主要可监测投放盘子；百度品专大量样本会进入说明和特殊样本处理，而不是直接纳入成本对比。",
    metrics: ["媒体 悠易互通", "媒体 抖音", "媒体 今日头条"],
    bullets: [
      "可监测媒体和不可监测点位需要分开看",
      "FREE 点位不参与成本对比，但仍保留在规模说明里"
    ]
  },
  {
    eyebrow: "Vehicle",
    title: "分车型具体表现",
    text: "ACC、BRE、INT 已形成基础车型拆解；执行器已重算 CTR、到达率、有效访客率和高意向率，不直接采用源表现成字段。",
    metrics: ["车型 ACC", "车型 BRE", "车型 INT"],
    bullets: [
      "车型级别适合看高意向成本和有效访客成本",
      "媒体和点位拆解建议放在车型之下继续展开"
    ]
  },
  {
    eyebrow: "Insight",
    title: "其他洞察",
    text: "补量、定向说明、小程序 adcode 说明等文本样本已被识别为 include_with_warning，可在配置层继续细化规则。",
    metrics: ["文本样本 include_with_warning"],
    bullets: [
      "这类内容适合在报告中单独给“说明块”",
      "而不是和正常投放样本完全混在一起"
    ]
  },
  {
    eyebrow: "Conclusion",
    title: "结论与行动建议",
    text: "当前阶段先以执行预览承接结论，后续可以继续要求系统补全：重点问题、原因归纳和下一步行动建议。",
    metrics: ["支持继续追问", "支持改写汇报口径"],
    bullets: [
      "适合输出给业务方看的短结论",
      "适合补充后续优化动作和风险提示"
    ]
  }
];

const STAGE_IDLE = "idle";
const STAGE_CLARIFICATION = "clarification";
const STAGE_PLAN = "plan";
const STAGE_REPORT = "report";
const STAGE_CHAT = "chat";

function createDefaultAgentCatalog() {
  return {
    "ad-analysis": {
      agent_id: "ad-analysis",
      name: "广告数据智能体",
      description: "面向广告投放 rawdata 的分析智能体",
    }
  };
}

function createEmptySessionState(agentId = "ad-analysis") {
  return {
    files: [],
    stage: STAGE_IDLE,
    agentId,
    taskType: "question_answering",
    artifactMode: "idle",
    conversationHistory: [],
    currentMessages: [],
    confirmations: {},
    cardLookup: {},
    reportSections: [],
    latestWorkflowResult: null,
    draftInput: "",
    statusText: "已创建新的分析会话。先上传 rawdata，再在这里发起月报或提问。",
    conversationStatus: "idle"
  };
}

function ensureSessionStore() {
  if (!window.sessionStore) {
    window.sessionStore = {
      "session-1": createEmptySessionState()
    };
  }
  if (!window.agentCatalog) {
    window.agentCatalog = createDefaultAgentCatalog();
  }
  if (!window.currentSessionId) {
    window.currentSessionId = "session-1";
  }
  if (!window.currentAgentId) {
    window.currentAgentId = "ad-analysis";
  }
}

function ensureSessionState(sessionId) {
  ensureSessionStore();
  if (!window.sessionStore[sessionId]) {
    window.sessionStore[sessionId] = createEmptySessionState();
  }
  return window.sessionStore[sessionId];
}

function getCurrentSessionState() {
  return ensureSessionState(window.currentSessionId);
}

function persistCurrentSessionState() {
  const state = ensureSessionState(window.currentSessionId);
  state.files = [...(window.currentFiles || [])];
  state.stage = window.currentStage || STAGE_IDLE;
  state.agentId = window.currentAgentId || "ad-analysis";
  state.taskType = window.currentTaskType || "question_answering";
  state.artifactMode = window.currentArtifactMode || "idle";
  state.conversationHistory = [...(window.currentConversationHistory || [])];
  state.currentMessages = [...(window.currentMessages || [])];
  state.confirmations = { ...(window.currentConfirmations || {}) };
  state.cardLookup = { ...(window.currentCardLookup || {}) };
  state.reportSections = [...(window.currentReportSections || [])];
  state.latestWorkflowResult = window.latestWorkflowResult || null;
  state.draftInput = document.getElementById("chat-input").value || "";
  state.statusText = document.getElementById("status-text").textContent || "";
  state.conversationStatus = document.getElementById("conversation-status").textContent || "idle";
}

function getLastUserRequest() {
  const source = window.currentConversationHistory || [];
  const latestUserMessage = [...source].reverse().find((item) => item.role === "user");
  return latestUserMessage?.text || "分析请求";
}

function syncWindowStateFromSession(sessionId) {
  const state = ensureSessionState(sessionId);
  window.currentSessionId = sessionId;
  window.currentAgentId = state.agentId || "ad-analysis";
  window.currentTaskType = state.taskType || "question_answering";
  window.currentArtifactMode = state.artifactMode || "idle";
  window.currentFiles = [...(state.files || [])];
  window.currentStage = state.stage || STAGE_IDLE;
  window.currentConversationHistory = [...(state.conversationHistory || [])];
  window.currentMessages = [...(state.currentMessages || [])];
  window.currentConfirmations = { ...(state.confirmations || {}) };
  window.currentCardLookup = { ...(state.cardLookup || {}) };
  window.currentReportSections = [...(state.reportSections || [])];
  window.latestWorkflowResult = state.latestWorkflowResult || null;
  document.getElementById("chat-input").value = state.draftInput || "";
  document.getElementById("status-text").textContent = state.statusText || "已切换会话。";
  document.getElementById("conversation-status").textContent = state.conversationStatus || "idle";
  document.getElementById("file-input").value = "";
  updateAgentUI();
  updateFileList();
  renderMessages();
  if (window.currentArtifactMode === "report" && window.latestWorkflowResult) {
    const result = window.latestWorkflowResult;
    renderReportFinal(result, result.plan || {}, result.execution || {}, result.llm || {});
  } else {
    renderArtifactIdle();
  }
}

function switchSession(sessionId) {
  persistCurrentSessionState();
  setView("workspace");
  setActiveSession(sessionId);
  syncWindowStateFromSession(sessionId);
}

function getSessionRecordsContainer() {
  return document.getElementById("session-records");
}

function getNextSessionNumber() {
  const items = getSessionRecordsContainer()?.querySelectorAll(".session-item") || [];
  return items.length + 1;
}

function setActiveSession(sessionId) {
  document.querySelectorAll(".session-item").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.sessionId === sessionId);
  });
}

function setActiveAgent(agentId) {
  document.querySelectorAll(".agent-item").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.agentId === agentId);
  });
}

function updateAgentUI() {
  const agent = window.agentCatalog?.[window.currentAgentId] || window.agentCatalog?.["ad-analysis"];
  setActiveAgent(window.currentAgentId);
  if (agent) {
    document.getElementById("view-title").textContent = agent.name;
  }
}

function createSessionRecord(label) {
  const container = getSessionRecordsContainer();
  if (!container) {
    return null;
  }
  const sessionId = `session-${Date.now()}`;
  window.sessionStore[sessionId] = createEmptySessionState(window.currentAgentId || "ad-analysis");
  const button = document.createElement("button");
  button.className = "sidebar-item session-item is-active";
  button.dataset.view = "workspace";
  button.dataset.sessionId = sessionId;
  button.textContent = label;
  button.addEventListener("click", () => {
    switchSession(sessionId);
  });
  container.prepend(button);
  setActiveSession(sessionId);
  return { sessionId, button };
}

function buildMessage(role, text, actions, extra = {}) {
  return { role, text, actions, ...extra };
}

function slugifyAgentName(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-")
    .replace(/^-+|-+$/g, "") || `agent-${Date.now()}`;
}

function addAgentToSidebar(agent) {
  const section = document.querySelector(".sidebar .sidebar-section");
  if (!section || document.querySelector(`.agent-item[data-agent-id="${agent.agent_id}"]`)) {
    return;
  }
  const newAgentButton = document.querySelector(".new-agent-entry");
  const button = document.createElement("button");
  button.className = "sidebar-item agent-item";
  button.dataset.view = "workspace";
  button.dataset.agentId = agent.agent_id;
  button.textContent = agent.name;
  button.addEventListener("click", () => {
    window.currentAgentId = agent.agent_id;
    getCurrentSessionState().agentId = agent.agent_id;
    updateAgentUI();
    setView("workspace");
    persistCurrentSessionState();
  });
  section.insertBefore(button, newAgentButton);
}

function buildAgentDraftFromNaturalLanguage(text) {
  const normalized = String(text || "").trim();
  const firstSentence = normalized.split(/[。.!?]/)[0] || "新智能体";
  const suggestedName = firstSentence.length > 18 ? `${firstSentence.slice(0, 18)}智能体` : `${firstSentence}智能体`;
  const rules = parseAssistantInput(normalized);
  return {
    agent_id: slugifyAgentName(suggestedName),
    name: suggestedName,
    description: normalized,
    file_types: normalized.includes("csv") ? "csv, xlsx" : "xlsx, csv",
    field_notes: normalized,
    metric_notes: "系统会根据你的业务说明自动生成关键指标与派生指标草稿。",
    rule_notes: rules.join("\n"),
    clarification_notes: "只在当前问题真的存在歧义时才发起澄清，不做固定问卷。",
    template_notes: "仅配置报告大结构；每次生成报告时再动态细化分析计划。",
    flow_notes: "普通问答在对话区完成；明确生成报告时才进入右侧产物面板。",
    assistant_input: normalized,
  };
}

function pushConversationMessage(role, text, extra = {}) {
  window.currentConversationHistory = window.currentConversationHistory || [];
  window.currentConversationHistory.push({ role, text, ...extra });
  persistCurrentSessionState();
}

function replaceConversationWithMessages(messages = []) {
  window.currentConversationHistory = messages
    .filter((item) => item && item.role && item.text)
    .map((item) => ({ ...item }));
}

function getClarificationCardMeta(cardId) {
  const meta = {
    reporting_month: {
      title: "报告月份确认",
      subtitle: "上传了多个 rawdata 或时间范围不一致时，先确定这次分析具体看哪些月份。"
    },
    cost_rule_confirmation: {
      title: "费用口径确认",
      subtitle: "先锁定成本口径，避免后续高意向成本和有效访客成本解释偏掉。"
    },
    free_slot_handling: {
      title: "FREE 点位处理",
      subtitle: "FREE 点位通常不参与成本对比，但仍可以保留在规模说明里。"
    },
    special_sample_handling: {
      title: "特殊样本处理",
      subtitle: "备注或 adslot 中的补量、特殊录入、定向说明等样本，需要先决定保留还是尽量排除。"
    }
  };
  return meta[cardId] || {
    title: "待确认项",
    subtitle: "这里是当前分析继续执行前需要确认的信息。"
  };
}

function getSelectedSummary(message) {
  const state = window.currentConfirmations || {};
  if (message.cardId === "reporting_month") {
    const selected = state.reporting_month || [];
    return selected.length ? `当前：${selected.join(" / ")}` : "当前：未确认";
  }
  if (message.cardId === "cost_rule_confirmation") {
    return state.cost_rule_confirmation ? "当前：已确认" : "当前：未确认";
  }
  if (message.cardId === "free_slot_handling") {
    return state.free_slot_handling === false ? "当前：保留 FREE 成本" : "当前：排除 FREE 成本";
  }
  if (message.cardId === "special_sample_handling") {
    return state.special_sample_handling === "exclude_warned_samples"
      ? "当前：尽量排除"
      : "当前：保留并标注";
  }
  return "当前：未确认";
}

function getMessageBadge(kind) {
  if (kind === "clarification") {
    return { label: "待确认", className: "" };
  }
  if (kind === "plan") {
    return { label: "分析计划", className: "plan" };
  }
  return null;
}

function scrollConversationToBottom() {
  const container = document.getElementById("message-stream");
  container.scrollTop = container.scrollHeight;
}

function getActionOptionsForCard(card) {
  if (card.options?.length) {
    const options = [...card.options];
    if (card.card_id === "reporting_month" && card.options.length > 1) {
      options.push("全部月份");
    }
    return options;
  }
  if (card.card_id === "cost_rule_confirmation") {
    return ["确认口径"];
  }
  if (card.card_id === "free_slot_handling") {
    return ["排除 FREE 成本", "保留 FREE 成本"];
  }
  if (card.card_id === "special_sample_handling") {
    return ["保留并标注", "尽量排除"];
  }
  return [];
}

function isActionSelected(cardId, action) {
  const state = window.currentConfirmations || {};
  if (cardId === "reporting_month") {
    const selected = state.reporting_month || [];
    if (action === "全部月份") {
      const options = window.currentCardLookup?.reporting_month?.options || [];
      return options.length > 1 && selected.length === options.length;
    }
    return selected.includes(action);
  }
  if (cardId === "cost_rule_confirmation") {
    return state.cost_rule_confirmation === true;
  }
  if (cardId === "free_slot_handling") {
    return (action === "排除 FREE 成本" && state.free_slot_handling !== false) ||
      (action === "保留 FREE 成本" && state.free_slot_handling === false);
  }
  if (cardId === "special_sample_handling") {
    return (action === "保留并标注" && state.special_sample_handling !== "exclude_warned_samples") ||
      (action === "尽量排除" && state.special_sample_handling === "exclude_warned_samples");
  }
  return false;
}

function renderMessages() {
  const container = document.getElementById("message-stream");
  const baseMessages = (window.currentMessages && window.currentMessages.length)
    ? window.currentMessages
    : (window.currentConversationHistory && window.currentConversationHistory.length)
      ? window.currentConversationHistory
      : defaultMessages;
  const source = [...baseMessages];
  if (window.isLoading) {
    source.push({
      role: "agent",
      kind: "loading",
      text: '<div class="typing-bubble"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>'
    });
  }
  if (!source.length) {
    container.innerHTML = '<div class="empty-state">上传数据后，在这里直接输入问题，或者点击“生成月报”。</div>';
    return;
  }
  container.innerHTML = source
    .map(
      (message) => {
        if (message.kind === "clarification_group") {
          const cards = message.cards || [];
          const isReady = cards.every((card) => {
            if (!card.required) {
              return true;
            }
            const state = window.currentConfirmations || {};
            if (card.card_id === "reporting_month") {
              return (state.reporting_month || []).length > 0;
            }
            if (card.card_id === "cost_rule_confirmation") {
              return typeof state.cost_rule_confirmation === "boolean";
            }
            if (card.card_id === "free_slot_handling") {
              return typeof state.free_slot_handling === "boolean";
            }
            if (card.card_id === "special_sample_handling") {
              return Boolean(state.special_sample_handling);
            }
            return false;
          });
          return `
            <div class="message-row agent">
              <div class="message-avatar agent-avatar">DA</div>
              <div class="message-body">
                <div class="message-role">agent</div>
                <div class="message-bubble agent clarification-group">
                  <div class="clarification-group">
                    <div class="clarification-group-title">分析前确认</div>
                    <div class="clarification-group-subtitle">先把这张确认卡填完，再进入下一步分析计划。</div>
                    ${cards.map((card) => `
                      <div class="clarification-item">
                        <div class="clarification-item-title">${card.title}</div>
                        <div class="clarification-item-text">${card.prompt}</div>
                        <div class="clarification-current">${getSelectedSummary({ cardId: card.card_id })}</div>
                        <div class="clarification-item-actions">
                          ${getActionOptionsForCard(card).map((action) => {
                            const active = isActionSelected(card.card_id, action) ? " is-selected" : "";
                            return `<button class="chip chip-button${active}" data-card-id="${card.card_id}" data-action="${action}">${action}</button>`;
                          }).join("")}
                        </div>
                      </div>
                    `).join("")}
                    <button class="stage-confirm" data-stage-action="confirm-clarifications" ${isReady ? "" : "disabled"}>确认并生成分析计划</button>
                  </div>
                </div>
              </div>
            </div>
          `;
        }
        if (message.kind === "plan_review") {
          return `
            <div class="message-row agent">
              <div class="message-avatar agent-avatar">DA</div>
              <div class="message-body">
                <div class="message-role">agent</div>
                <div class="message-bubble agent plan-review">
                  <div class="plan-review-title">分析计划</div>
                  <div class="plan-review-subtitle">确认下面的结构化计划后，才开始最终生成报告。</div>
                  <ol class="plan-review-list">
                    ${(message.steps || []).map((step) => `<li>${step}</li>`).join("")}
                  </ol>
                  <button class="stage-confirm" data-stage-action="confirm-plan">确认并生成月报</button>
                </div>
              </div>
            </div>
          `;
        }
        if (message.kind === "error_retry") {
          return `
            <div class="message-row agent">
              <div class="message-avatar agent-avatar">DA</div>
              <div class="message-body">
                <div class="message-role">agent</div>
                <div class="message-bubble agent">
                  <div>${message.text}</div>
                  <div class="inline-actions">
                    <button class="chip chip-button" data-retry-analysis="true">重试</button>
                  </div>
                </div>
              </div>
            </div>
          `;
        }
        const isUser = message.role === "user";
        const bubbleClass = message.role === "agent" ? "agent" : message.role === "user" ? "user" : "system";
        const rowClass = isUser ? "user" : message.role === "system" ? "system" : "agent";
        const avatarClass = isUser ? "user-avatar" : message.role === "system" ? "system-avatar" : "agent-avatar";
        const avatarText = isUser ? "你" : message.role === "system" ? "SYS" : "DA";
        const avatar = `<div class="message-avatar ${avatarClass}">${avatarText}</div>`;
        const badge = getMessageBadge(message.kind);
        const clarificationMeta = message.kind === "clarification" ? getClarificationCardMeta(message.cardId) : null;
        const queryResultCard = message.queryResult ? renderQueryResultCard(message.queryResult) : "";
        return `
        <div class="message-row ${rowClass}">
          ${isUser ? "" : avatar}
          <div class="message-body">
            <div class="message-role">${message.role}</div>
            <div class="message-bubble ${bubbleClass}${message.kind ? ` ${message.kind}` : ""}">
              ${
                badge
                  ? `<div class="message-badge${badge.className ? ` ${badge.className}` : ""}">${badge.label}</div>`
                  : ""
              }
              ${
                clarificationMeta
                  ? `
                    <div class="clarification-card-head">
                      <div class="clarification-title">${clarificationMeta.title}</div>
                      <div class="clarification-subtitle">${clarificationMeta.subtitle}</div>
                      <div>${message.text}</div>
                      <div class="clarification-current">${getSelectedSummary(message)}</div>
                    </div>
                  `
                  : `<div>${message.text}</div>`
              }
              ${queryResultCard}
            </div>
          ${
            message.actions?.length
              ? `<div class="inline-actions${message.kind === "clarification" ? " clarification-actions" : ""}">${message.actions
                  .map((action) => {
                    const active = message.cardId && isActionSelected(message.cardId, action)
                      ? " is-selected"
                      : "";
                    const attrs = message.cardId
                      ? `data-card-id="${message.cardId}" data-action="${action}"`
                      : "";
                    return `<button class="chip chip-button${active}" ${attrs}>${action}</button>`;
                  })
                  .join("")}</div>`
              : ""
          }
        </div>
          ${isUser ? avatar : ""}
        </div>
      `;
      }
    )
    .join("");
  scrollConversationToBottom();
}

function setLoadingState(isLoading) {
  window.isLoading = isLoading;
  document.getElementById("send-button").disabled = isLoading;
  renderMessages();
}

function formatMetricValue(value, kind = "number") {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return String(value);
  }
  if (kind === "percent") {
    return `${(numeric * 100).toFixed(2)}%`;
  }
  if (kind === "integer") {
    return Math.round(numeric).toLocaleString("zh-CN");
  }
  return numeric.toLocaleString("zh-CN", {
    minimumFractionDigits: numeric >= 100 ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

function getMetricKind(metricKey) {
  if (["ctr", "arrival_rate", "valid_visitor_rate", "high_intent_rate"].includes(metricKey)) {
    return "percent";
  }
  if (["pv", "click", "arrivals", "valid_visitors", "high_intent_visitors"].includes(metricKey)) {
    return "integer";
  }
  return "number";
}

function getGoalLabel(goal) {
  return {
    confirm_presence: "确认是否存在",
    retrieve_value: "查询具体值",
    inspect_breakdown: "查看拆解",
    compare_entities: "做对比",
  }[goal] || "查询分析";
}

function getDimensionLabel(dimension) {
  return {
    month: "月份",
    vehicle: "车型",
    media: "媒体",
    placement: "点位",
  }[dimension] || dimension;
}

function renderQueryPlanSummary(querySpec = {}) {
  const filters = querySpec.filters || {};
  const activeFilters = Object.entries(filters)
    .filter(([, value]) => Boolean(value))
    .map(([key, value]) => `${getDimensionLabel(key)}=${value}`);
  const dimensions = (querySpec.requested_dimensions || []).map(getDimensionLabel);
  const rows = [
    { label: "分析目标", value: getGoalLabel(querySpec.goal) },
    { label: "核心指标", value: querySpec.metric_label || "-" },
    { label: "筛选条件", value: activeFilters.length ? activeFilters.join(" / ") : "无固定筛选" },
    { label: "关注维度", value: dimensions.length ? dimensions.join(" + ") : "不拆解" },
  ];

  if (querySpec.sort_direction) {
    rows.push({
      label: "排序方式",
      value: `${querySpec.sort_direction === "asc" ? "升序" : "降序"}${querySpec.limit ? ` · Top ${querySpec.limit}` : ""}`,
    });
  }

  return `
    <div class="query-plan-box">
      <div class="query-plan-title">本次查询计划</div>
      <div class="query-plan-grid">
        ${rows.map((row) => `
          <div class="query-plan-row">
            <div class="query-plan-label">${row.label}</div>
            <div class="query-plan-value">${row.value}</div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function renderQueryResultCard(queryResult) {
  if (!queryResult) {
    return "";
  }
  const metricKey = queryResult.metric_key || "high_intent_cost";
  const metricLabel = queryResult.metric_label || "高意向成本";
  const metricKind = getMetricKind(metricKey);
  const rows = queryResult.entries || [];
  const interpretation = queryResult.query_spec?.interpretation || "";
  const traceSteps = queryResult.trace_steps || [];
  const followUpOptions = queryResult.follow_up_options || [];
  const metaSummary = [
    `模式：${queryResult.mode}`,
    `结果数：${rows.length}`,
    `规划：${queryResult.query_spec?.planner_source === "llm_planner" ? "LLM" : "规则兜底"}`,
  ];
  const queryPlanSummary = renderQueryPlanSummary(queryResult.query_spec || {});

  if (queryResult.mode === "existence") {
    return `
      <div class="query-card">
      <div class="query-card-head">
        <div class="query-card-title">${queryResult.title || "查询结果"}</div>
        <div class="query-card-mode">是否存在</div>
      </div>
      <div class="query-card-meta">${metaSummary.join(" · ")}</div>
      ${queryPlanSummary}
      ${interpretation ? `<div class="query-card-interpretation">${interpretation}</div>` : ""}
      <div class="query-card-summary ${queryResult.exists ? "positive" : "neutral"}">
        ${queryResult.exists ? "存在相关投放数据" : "没有匹配到相关投放数据"}
      </div>
    </div>
    `;
  }

  if (queryResult.mode === "clarification_needed") {
    return `
      <div class="query-card">
        <div class="query-card-head">
          <div class="query-card-title">${queryResult.title || "需要确认"}</div>
          <div class="query-card-mode">待补充信息</div>
        </div>
        <div class="query-card-meta">${metaSummary.join(" · ")}</div>
        ${queryPlanSummary}
        ${interpretation ? `<div class="query-card-interpretation">${interpretation}</div>` : ""}
        <div class="query-card-summary neutral">${queryResult.answer_text}</div>
        ${
          (queryResult.clarification_options || []).length
            ? `
              <div class="inline-actions query-clarification-actions">
                ${(queryResult.clarification_options || []).map((option) => `
                  <button class="chip chip-button" data-query-clarification="${option}">${option}</button>
                `).join("")}
              </div>
            `
            : ""
        }
      </div>
    `;
  }

  if (!rows.length) {
    return `
      <div class="query-card">
        <div class="query-card-head">
          <div class="query-card-title">${queryResult.title || "查询结果"}</div>
          <div class="query-card-mode">空结果</div>
        </div>
        <div class="query-card-meta">${metaSummary.join(" · ")}</div>
        ${queryPlanSummary}
        ${interpretation ? `<div class="query-card-interpretation">${interpretation}</div>` : ""}
        <div class="query-card-summary neutral">当前筛选范围没有匹配到可用数据。</div>
      </div>
    `;
  }

  const renderChildren = (children = []) => {
    if (!children.length) {
      return "";
    }
    const childMax = Math.max(...children.map((child) => Number(child[metricKey]) || 0), 1);
    return `
      <div class="query-children">
        ${children.map((child) => `
          <div class="query-child-row">
            <span class="query-child-label">${child.label}</span>
            <div class="query-bar-track child">
              <div class="query-bar-fill" style="width:${Math.max(((Number(child[metricKey]) || 0) / childMax) * 100, 6)}%"></div>
            </div>
            <span class="query-child-value">${formatMetricValue(child[metricKey], metricKind)}</span>
          </div>
        `).join("")}
      </div>
    `;
  };

  const maxValue = Math.max(...rows.map((entry) => Number(entry[metricKey]) || 0), 1);
  const modeLabel = {
    breakdown: "拆解结果",
    comparison: "对比结果",
    single_value: "数值结果",
  }[queryResult.mode] || "查询结果";

  return `
    <div class="query-card">
      <div class="query-card-head">
        <div class="query-card-title">${queryResult.title || "查询结果"}</div>
        <div class="query-card-mode">${modeLabel}</div>
      </div>
      <div class="query-card-meta">${metaSummary.join(" · ")}</div>
      ${queryPlanSummary}
      ${interpretation ? `<div class="query-card-interpretation">${interpretation}</div>` : ""}
      <div class="query-card-metric">${metricLabel}</div>
      <div class="query-table">
        <div class="query-table-head">
          <span>维度</span>
          <span>相对表现</span>
          <span>${metricLabel}</span>
        </div>
        ${rows.map((entry) => `
          <div class="query-table-row ${entry.children?.length ? "has-children" : ""}">
            <div class="query-table-main">
              <span class="query-table-label">${entry.label}</span>
              <div class="query-bar-track">
                <div class="query-bar-fill" style="width:${Math.max(((Number(entry[metricKey]) || 0) / maxValue) * 100, 6)}%"></div>
              </div>
              <span class="query-table-value">${formatMetricValue(entry[metricKey], metricKind)}</span>
            </div>
            ${renderChildren(entry.children)}
          </div>
        `).join("")}
      </div>
      ${
        traceSteps.length
          ? `
            <details class="query-trace">
              <summary>查看本次查询过程</summary>
              <div class="query-trace-list">
                ${traceSteps.map((item) => `
                  <div class="query-trace-row">
                    <div class="query-trace-step">${item.step}</div>
                    <div class="query-trace-detail">${item.detail}</div>
                  </div>
                `).join("")}
              </div>
            </details>
          `
          : ""
      }
      ${
        followUpOptions.length
          ? `
            <div class="query-followups">
              <div class="query-followups-title">继续追问</div>
              <div class="inline-actions">
                ${followUpOptions.map((option) => `
                  <button class="chip chip-button query-followup-button" data-query-followup="${option}">${option}</button>
                `).join("")}
              </div>
            </div>
          `
          : ""
      }
    </div>
  `;
}

function buildChartSection(title, subtitle, entries, valueKey, valueKind = "number") {
  if (!entries.length) {
    return "";
  }
  const maxValue = Math.max(...entries.map((entry) => Number(entry[valueKey]) || 0), 1);
  return `
    <article class="section-card chart-card">
      <div class="section-eyebrow">Chart</div>
      <h3>${title}</h3>
      <p>${subtitle}</p>
      <div class="chart-list">
        ${entries.map((entry) => {
          const rawValue = Number(entry[valueKey]) || 0;
          const width = Math.max((rawValue / maxValue) * 100, rawValue > 0 ? 8 : 0);
          return `
            <div class="chart-row">
              <div class="chart-label">${entry.label}</div>
              <div class="chart-bar-track">
                <div class="chart-bar-fill" style="width:${width}%"></div>
              </div>
              <div class="chart-value">${formatMetricValue(entry[valueKey], valueKind)}</div>
            </div>
          `;
        }).join("")}
      </div>
    </article>
  `;
}

function buildTableSection(title, entries, valueKind = "number") {
  if (!entries.length) {
    return "";
  }
  return `
    <article class="section-card">
      <div class="section-eyebrow">Data</div>
      <h3>${title}</h3>
      <div class="data-table">
        <div class="data-row data-head">
          <span>维度</span>
          <span>高意向成本</span>
          <span>点击率</span>
        </div>
        ${entries.map((entry) => `
          <div class="data-row">
            <span>${entry.label}</span>
            <span>${formatMetricValue(entry.high_intent_cost, valueKind)}</span>
            <span>${formatMetricValue(entry.ctr, "percent")}</span>
          </div>
        `).join("")}
      </div>
    </article>
  `;
}

function buildQueryResultSection(queryResult) {
  if (!queryResult?.entries?.length) {
    return "";
  }
  return buildTableSection(queryResult.title || "查询结果", queryResult.entries);
}

function buildVisualEntries(sourceObject = {}, limit = 6) {
  return Object.entries(sourceObject)
    .map(([label, metrics]) => ({
      label,
      ...metrics,
    }))
    .filter((entry) => entry.high_intent_cost !== null || entry.ctr !== null || entry.effective_cost > 0)
    .slice(0, limit);
}

function renderProcessDetails(result, execution) {
  const datasets = result.datasets || [];
  const confirmations = window.currentConfirmations || {};
  const confirmationText = [
    confirmations.reporting_month?.length ? `报告月份：${confirmations.reporting_month.join(" / ")}` : "报告月份：待按文件候选确认",
    typeof confirmations.cost_rule_confirmation === "boolean" ? "费用口径：已确认" : "费用口径：待确认",
    confirmations.special_sample_handling === "exclude_warned_samples" ? "特殊样本：尽量排除" : "特殊样本：保留并标注",
  ].join("；");
  const mappingSummary = datasets.map((dataset) => {
    const recognized = dataset.header_mapping?.recognized?.length || 0;
    const unmapped = dataset.header_mapping?.unmapped?.length || 0;
    return `${dataset.file_name}：识别 ${recognized} 个字段${unmapped ? `，未映射 ${unmapped} 个` : ""}`;
  }).join("；");
  const timeSummary = datasets.map((dataset) => {
    const candidates = (dataset.reporting_months?.candidates || []).map((item) => item.value).filter(Boolean);
    return `${dataset.file_name}：候选月份 ${candidates.join(" / ") || "未识别"}`;
  }).join("；");

  renderTimeline([
    {
      title: "确认本次报告月份、费用口径和特殊样本处理规则",
      detail: confirmationText,
    },
    {
      title: "读取上传文件并校验核心字段映射是否完整",
      detail: mappingSummary || "等待文件解析结果。",
    },
    {
      title: "解析投放时间区间并确定本次报告的数据范围",
      detail: timeSummary || "等待时间区间解析结果。",
    },
  ]);
}

function renderReportSections() {
  const container = document.getElementById("report-sections");
  const source = window.currentReportSections || defaultReportSections;
  const executionOverview = window.latestWorkflowResult?.execution?.overview || {};
  const queryResult = window.latestWorkflowResult?.execution?.query_result;
  const monthEntries = buildVisualEntries(executionOverview.by_month || {}, 6);
  const vehicleEntries = buildVisualEntries(executionOverview.by_vehicle || {}, 6);
  const mediaEntries = buildVisualEntries(executionOverview.top_media || {}, 6);
  const placementEntries = buildVisualEntries(executionOverview.top_placements || {}, 6);
  const visualBlocks = [
    buildQueryResultSection(queryResult),
    buildChartSection("月份高意向成本", "按月份重算后的高意向访客成本。", monthEntries, "high_intent_cost"),
    buildChartSection("车型高意向成本", "按车型看高意向成本表现。", vehicleEntries, "high_intent_cost"),
    buildChartSection("媒体点击率", "按媒体看点击率表现。", mediaEntries, "ctr", "percent"),
    buildChartSection("点位类型高意向成本", "按点位类型看成本表现。", placementEntries, "high_intent_cost"),
    buildTableSection("分媒体明细", mediaEntries),
    buildTableSection("分点位类型明细", placementEntries),
    buildTableSection("分车型明细", vehicleEntries),
  ].filter(Boolean).join("");

  const textBlocks = source
    .map(
      (section) => `
        <article class="section-card">
          ${section.eyebrow ? `<div class="section-eyebrow">${section.eyebrow}</div>` : ""}
          <h3>${section.title}</h3>
          <p>${section.text}</p>
          ${
            section.metrics?.length
              ? `<div class="section-metrics">${section.metrics
                  .map((item) => `<span class="section-metric">${item}</span>`)
                  .join("")}</div>`
              : ""
          }
          ${
            section.bullets
              ? `<ul class="section-list">${section.bullets
                  .map((item) => `<li>${item}</li>`)
                  .join("")}</ul>`
              : ""
          }
        </article>
      `
    )
    .join("");
  container.innerHTML = visualBlocks + textBlocks;
}

function renderMetadata(items = []) {
  const container = document.getElementById("report-metadata");
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">等待上传数据并运行分析。</div>';
    return;
  }
  container.innerHTML = items
    .map(
      (item) => `
        <div class="meta-item">
          <div class="meta-item-label">${item.label}</div>
          <div class="meta-item-value">${item.value}</div>
        </div>
      `
    )
    .join("");
}

function renderReportOutline(items = []) {
  const container = document.getElementById("report-outline");
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">报告目录会随着执行结果自动生成。</div>';
    return;
  }
  container.innerHTML = items
    .map(
      (item, index) => `
        <div class="report-outline-item">
          <div class="report-outline-index">${String(index + 1).padStart(2, "0")}</div>
          <div class="report-outline-text">${item.title}</div>
        </div>
      `
    )
    .join("");
}

function getConfigDraftStorageKey() {
  return "data-agent-codex-config-draft-v1";
}

function buildConfigDraftFromSummary(summary = {}) {
  const agent = summary.agent || {};
  return {
    agent_name: agent.name || "",
    file_types: (agent.supported_file_types || []).join(", "),
    agent_description: agent.description || "",
    field_notes: "",
    metric_notes: "",
    rule_notes: "",
    clarification_notes: "",
    template_notes: "",
    flow_notes: "",
    assistant_input: "",
  };
}

function loadStoredConfigDraft() {
  try {
    const raw = localStorage.getItem(getConfigDraftStorageKey());
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch (_error) {
    return null;
  }
}

function getCurrentConfigDraft() {
  if (!window.configDraft) {
    const summary = window.configSummary || {};
    window.configDraft = loadStoredConfigDraft() || buildConfigDraftFromSummary(summary);
  }
  return window.configDraft;
}

function setConfigSaveStatus(text) {
  const target = document.getElementById("config-save-status");
  if (target) {
    target.textContent = text;
  }
}

function renderConfigDraftForm() {
  const draft = getCurrentConfigDraft();
  const setValue = (id, value) => {
    const element = document.getElementById(id);
    if (element) {
      element.value = value || "";
    }
  };
  setValue("cfg-agent-name", draft.agent_name);
  setValue("cfg-file-types", draft.file_types);
  setValue("cfg-agent-desc", draft.agent_description);
  setValue("cfg-field-notes", draft.field_notes);
  setValue("cfg-metric-notes", draft.metric_notes);
  setValue("cfg-rule-notes", draft.rule_notes);
  setValue("cfg-clarification-notes", draft.clarification_notes);
  setValue("cfg-template-notes", draft.template_notes);
  setValue("cfg-flow-notes", draft.flow_notes);
  setValue("assistant-input-preview", draft.assistant_input);
}

function collectConfigDraftFromForm() {
  const readValue = (id) => document.getElementById(id)?.value?.trim?.() || "";
  window.configDraft = {
    ...getCurrentConfigDraft(),
    agent_name: readValue("cfg-agent-name"),
    file_types: readValue("cfg-file-types"),
    agent_description: readValue("cfg-agent-desc"),
    field_notes: readValue("cfg-field-notes"),
    metric_notes: readValue("cfg-metric-notes"),
    rule_notes: readValue("cfg-rule-notes"),
    clarification_notes: readValue("cfg-clarification-notes"),
    template_notes: readValue("cfg-template-notes"),
    flow_notes: readValue("cfg-flow-notes"),
    assistant_input: readValue("assistant-input-preview"),
  };
}

function saveConfigDraftToLocal() {
  collectConfigDraftFromForm();
  localStorage.setItem(getConfigDraftStorageKey(), JSON.stringify(window.configDraft));
  setConfigSaveStatus("draft saved");
}

function parseAssistantInput(text) {
  const suggestions = [];
  const normalized = String(text || "").trim();
  if (!normalized) {
    return suggestions;
  }
  if (normalized.includes("FREE")) {
    suggestions.push("规则：FREE 点位默认不纳入成本对比。");
  }
  if (normalized.includes("补量") || normalized.includes("备注")) {
    suggestions.push("规则：备注/adslot 中的补量样本标记为特殊样本。");
  }
  if (normalized.includes("月份") || normalized.includes("跨月")) {
    suggestions.push("流程：报告月份需要先确认，再进入分析计划。");
  }
  if (!suggestions.length) {
    suggestions.push("已解析为通用配置要求，建议补充字段、指标或规则关键词。");
  }
  return suggestions;
}

function renderAssistantSuggestions(items = []) {
  const target = document.getElementById("assistant-suggestion-list");
  if (!target) {
    return;
  }
  target.innerHTML = items.map((item) => `<div class="assistant-suggestion">${item}</div>`).join("");
}

function activateConfigModule(moduleId) {
  const aliasMap = {
    basic: "agent-builder",
    fields: "data-semantics",
    metrics: "analysis-rules",
    rules: "analysis-rules",
    clarification: "analysis-rules",
    template: "report-output",
    flow: "report-output",
  };
  const resolvedModuleId = aliasMap[moduleId] || moduleId;
  const targetButton = document.querySelector(`.module-item[data-module="${resolvedModuleId}"]`);
  const targetBlock = document.querySelector(`[data-module-block="${resolvedModuleId}"]`);
  if (targetButton) {
    setActiveButton(".module-item", targetButton);
    const title = targetButton.textContent.trim();
    document.getElementById("view-title").textContent = title;
  }
  if (targetBlock) {
    targetBlock.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderConfigStudio(summary) {
  const summaryGrid = document.getElementById("config-summary-grid");
  const fieldTable = document.getElementById("config-field-table");
  const metricGrid = document.getElementById("config-metric-grid");
  const ruleList = document.getElementById("config-rule-list");
  const clarificationList = document.getElementById("config-clarification-list");
  const templateList = document.getElementById("config-template-list");
  const assistantInput = document.getElementById("assistant-input-preview");
  const assistantSuggestions = document.getElementById("assistant-suggestion-list");

  const agent = summary.agent || {};
  const datasetProfile = summary.dataset_profile || {};
  const fields = summary.fields || [];
  const metrics = summary.metrics || [];
  const filters = summary.filters || [];
  const exclusions = summary.metric_specific_exclusions || [];
  const clarificationFlow = summary.clarification_flow || [];
  const templates = summary.templates || [];

  summaryGrid.innerHTML = [
    { label: "智能体", value: agent.name || "未命名" },
    { label: "支持文件", value: (agent.supported_file_types || []).join(" / ") || "-" },
    { label: "核心能力", value: String((agent.capabilities || []).length) },
    { label: "字段规模", value: String(fields.length) }
  ]
    .map(
      (item) => `
        <div class="config-summary-card">
          <div class="config-summary-label">${item.label}</div>
          <div class="config-summary-value">${item.value}</div>
        </div>
      `
    )
    .join("");

  const headRow = `
    <div class="config-row config-head">
      <span>原始字段</span>
      <span>标准字段</span>
      <span>角色</span>
      <span>说明</span>
    </div>
  `;
  const fieldRows = fields.slice(0, 8).map((field) => `
    <div class="config-row">
      <span>${field.display_name || "-"}</span>
      <span>${field.field_id || "-"}</span>
      <span>${field.semantic_role || "-"}</span>
      <span>${field.disambiguation_hint || (field.aliases || []).slice(0, 2).join(" / ") || "-"}</span>
    </div>
  `);
  fieldTable.innerHTML = headRow + fieldRows.join("");

  metricGrid.innerHTML = metrics.slice(0, 8).map((metric) => `
    <div class="config-chip-card">
      <div class="config-chip-label">${metric.type || "metric"}</div>
      <div class="config-chip-value">${metric.name || metric.metric_id}</div>
      <div class="config-chip-meta">${metric.formula || metric.field || metric.aggregation_rule || "-"}</div>
    </div>
  `).join("");

  const ruleCards = [
    ...filters.map((rule) => ({
      title: rule.description || rule.rule_id || "过滤规则",
      text: `${rule.expression?.field || "-"} ${rule.expression?.op || "-"} ${rule.expression?.value || "-"}`
    })),
    ...exclusions.map((rule) => ({
      title: rule.rule_id || "指标级排除",
      text: `${(rule.applies_to_metrics || []).join("、")} | 条件：${JSON.stringify(rule.when)}`
    }))
  ];
  ruleList.className = "rule-list";
  ruleList.innerHTML = ruleCards.map((rule) => `
    <div class="rule-card">
      <div class="rule-title">${rule.title}</div>
      <div class="rule-text">${rule.text}</div>
    </div>
  `).join("");

  clarificationList.className = "clarification-list";
  clarificationList.innerHTML = clarificationFlow.map((item, index) => `
    <div class="clarification-card">
      <div class="template-label">STEP ${index + 1}</div>
      <div class="template-title">${item.card_id || item}</div>
      <div class="clarification-meta">${item.reason || "当前分析流程中的标准确认节点"}</div>
    </div>
  `).join("");

  templateList.className = "template-list";
  templateList.innerHTML = templates.map((template) => `
    <div class="template-card">
      <div class="template-label">${(template.trigger_intents || []).join(" / ") || "template"}</div>
      <div class="template-title">${template.name || template.template_id}</div>
      <div class="template-meta">${datasetProfile.summary || "数据分析模板"}</div>
      <div class="template-section-list">
        ${(template.sections || []).map((section) => `<span class="template-section-chip">${section.title}</span>`).join("")}
      </div>
    </div>
  `).join("");

  if (!window.configDraft) {
    const stored = loadStoredConfigDraft();
    window.configDraft = stored || {
      ...buildConfigDraftFromSummary(summary),
      field_notes: `核心字段：${fields.slice(0, 6).map((field) => field.field_id).join(", ")}`,
      metric_notes: metrics.slice(0, 4).map((metric) => `${metric.metric_id || metric.name}: ${metric.formula || metric.field || "-"}`).join("\n"),
      rule_notes: filters.slice(0, 3).map((rule) => rule.description || rule.rule_id).join("\n"),
      clarification_notes: clarificationFlow.map((item) => item.card_id || item).join("\n"),
      template_notes: templates.map((template) => template.name || template.template_id).join("\n"),
      flow_notes: (agent.default_task_flow || []).join(" -> "),
      assistant_input: "如果备注里有补量就标记为特殊样本；FREE 点位不要纳入成本对比；文件名月份和投放时间不一致时先让我确认月份。",
    };
  }
  renderConfigDraftForm();

  const defaultSuggestions = [
    "规则 1：文本语义字段 remark / adslot 进入特殊样本处理流。",
    "规则 2：广告类型 = FREE 时，成本相关指标默认排除。",
    `规则 3：报告月份遵循 ${((summary.report_period_resolution || {}).priority || []).join(" -> ")}。`
  ];
  renderAssistantSuggestions(defaultSuggestions);
  if (assistantInput && !assistantInput.value) {
    assistantInput.value = window.configDraft.assistant_input || "";
  }
  if (assistantSuggestions && !assistantSuggestions.innerHTML.trim()) {
    renderAssistantSuggestions(defaultSuggestions);
  }
}

async function loadConfigStudio() {
  try {
    const response = await fetch(apiUrl("/api/config-summary"));
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "加载配置失败");
    }
    window.configSummary = payload;
    renderConfigStudio(payload);
    setConfigSaveStatus("loaded");
  } catch (error) {
    const summaryGrid = document.getElementById("config-summary-grid");
    const message = error.message === "Failed to fetch"
      ? `配置读取失败：无法连接本地服务。请打开 ${DEFAULT_LOCAL_API_BASE}`
      : `配置读取失败：${error.message}`;
    summaryGrid.innerHTML = `<div class="empty-state">${message}</div>`;
  }
}

function renderTimeline(items = []) {
  const container = document.getElementById("report-timeline");
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">等待生成计划和执行状态。</div>';
    return;
  }
  container.innerHTML = items
    .map(
      (item) => `
        <details class="report-detail">
          <summary class="report-detail-summary">${item.title || item.step}</summary>
          <div class="report-detail-body">${item.detail}</div>
        </details>
      `
    )
    .join("");
}

function setArtifactMode(mode) {
  window.currentArtifactMode = mode;
  const pill = document.getElementById("artifact-mode-pill");
  if (pill) {
    pill.textContent = mode;
  }
}

function renderArtifactIdle() {
  const panel = document.querySelector(".report-panel");
  panel.classList.add("is-empty");
  setArtifactMode("idle");
  document.getElementById("report-sections").innerHTML = '<div class="empty-state">普通问答直接在对话里完成。只有明确要求生成报告时，这里才会出现正式产物。</div>';
  document.getElementById("report-outline").innerHTML = "";
  document.getElementById("report-metadata").innerHTML = "";
  document.getElementById("report-timeline").innerHTML = "";
  document.getElementById("summary-reporting-month").textContent = "未生成";
  document.getElementById("summary-status").textContent = "等待报告任务";
  document.getElementById("summary-request").textContent = "仅在生成报告时展示";
  document.getElementById("report-title").textContent = "尚未生成正式产物";
  document.getElementById("report-subtitle").textContent = "普通问答会直接留在对话区。只有明确要求生成报告时，右侧才会展开正式产物。";
}

function renderReportFinal(result, plan, execution, llm) {
  const panel = document.querySelector(".report-panel");
  panel.classList.remove("is-empty");
  setArtifactMode("report");

  const sections = llm.report_sections?.length ? llm.report_sections : window.currentReportSections || defaultReportSections;
  window.currentReportSections = sections;

  updateSummary(result, plan, execution);
  updateReportHeader(result, plan);
  renderMetadata([
    { label: "数据文件", value: `${result.datasets.length} 个` },
    { label: "样本范围", value: `${execution.row_stats?.rows_after_filters || 0} / ${execution.row_stats?.total_rows_scanned || 0} 行` },
    { label: "报告类型", value: plan.task_variant || plan.task_type || "analysis" },
    { label: "当前请求", value: result.plan?.summary || getLastUserRequest() || "-" }
  ]);
  renderProcessDetails(result, execution);
  renderReportOutline(getTemplateSectionsForPlan(plan).length ? getTemplateSectionsForPlan(plan) : sections);
  renderReportSections();
  persistCurrentSessionState();
}

function updateSummary(result, plan, execution) {
  const reportingMonthElement = document.getElementById("summary-reporting-month");
  const statusElement = document.getElementById("summary-status");
  const requestElement = document.getElementById("summary-request");
  const conversationStatus = document.getElementById("conversation-status");

  const selectedMonths = window.currentConfirmations?.reporting_month?.length
    ? window.currentConfirmations.reporting_month
    : result.datasets.flatMap((dataset) => dataset.reporting_month_candidates || []);
  const monthText = selectedMonths.length ? [...new Set(selectedMonths)].join(" / ") : "待确认";
  const hasCards = (result.clarification_cards || []).length > 0;
  const statusText = hasCards ? "待确认后可继续执行" : "已进入执行预览";

  reportingMonthElement.textContent = plan.task_type === "monthly_report" ? `报告 · ${monthText}` : "问答";
  statusElement.textContent = statusText;
  requestElement.textContent = getLastUserRequest();
  conversationStatus.textContent = hasCards ? "plan_pending_confirmation" : "executing_preview";
}

function updateReportHeader(result, plan) {
  const titleElement = document.getElementById("report-title");
  const subtitleElement = document.getElementById("report-subtitle");
  const requestText = getLastUserRequest();
  const monthText = window.currentConfirmations?.reporting_month?.length
    ? window.currentConfirmations.reporting_month.join(" / ")
    : result.datasets.flatMap((dataset) => dataset.reporting_month_candidates || []).filter(Boolean).join(" / ");
  const variant = plan.task_variant || plan.task_type || "analysis";

  titleElement.textContent =
    variant === "single_month" ? `广告投放月报 · ${monthText || "单月"}` :
    variant === "multi_month" ? `广告投放跨月报告 · ${monthText || "跨月"}` :
    "正式分析产物";
  subtitleElement.textContent = `当前任务：${requestText}。这里只承接最终报告，不承接普通对话问答。`;
}

function getTemplateSectionsForPlan(plan) {
  const templates = window.configSummary?.templates || [];
  const variant = plan.task_variant || plan.task_type;
  if (!templates.length) {
    return [];
  }
  if (variant === "multi_month") {
    return templates.find((template) => template.template_id?.includes("multi-month"))?.sections || [];
  }
  if (variant === "single_month" || variant === "monthly_report") {
    return templates.find((template) => template.template_id?.includes("single-month"))?.sections || [];
  }
  return templates[0].sections || [];
}

function setView(view) {
  document.querySelectorAll(".view").forEach((element) => {
    element.classList.toggle("is-visible", element.id === `${view}-view`);
  });
  if (view === "config") {
    document.getElementById("view-title").textContent = "智能体设计";
  } else {
    updateAgentUI();
  }
  document.querySelectorAll(".topbar-actions [data-view], .sidebar-section .sidebar-item:not(.session-item)[data-view]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === view);
  });
}

function setActiveButton(groupSelector, targetButton) {
  document.querySelectorAll(groupSelector).forEach((button) => {
    button.classList.toggle("is-active", button === targetButton);
  });
}

function resetWorkspaceState() {
  window.sessionStore[window.currentSessionId] = createEmptySessionState(window.currentAgentId || "ad-analysis");
  syncWindowStateFromSession(window.currentSessionId);
}

function handleSidebarAction(button) {
  const label = button.textContent.trim();
  if (button.dataset.view) {
    setView(button.dataset.view);
    setActiveButton(".sidebar-section .sidebar-item:not(.session-item)", button);
    if (button.dataset.configModule) {
      activateConfigModule(button.dataset.configModule);
    }
    return;
  }

  if (label.includes("运行记录") || label.includes("模板中心")) {
    setView("config");
    document.getElementById("view-title").textContent = label;
    setActiveButton(".sidebar-section .sidebar-item", button);
  }
}

function isReportTask(taskType, requestText) {
  return taskType === "monthly_report" || /(月报|报告|复盘|汇报)/.test(requestText || "");
}

function getRelevantClarificationCards(result, taskType) {
  if (!isReportTask(taskType, getLastUserRequest())) {
    return [];
  }
  const currentReportingMonth = window.currentConfirmations?.reporting_month || [];
  return (result.clarification_cards || []).filter((card) => {
    if (card.card_id === "reporting_month") {
      const options = card.options || [];
      return options.length > 1 && currentReportingMonth.length === 0;
    }
    return false;
  });
}

function renderWorkflowResult(result) {
  const plan = result.plan || {};
  const execution = result.execution || {};
  const cards = getRelevantClarificationCards(result, window.currentTaskType);
  const llm = result.llm || {};
  const queryResult = execution.query_result || null;
  const currentMessages = [...(window.currentConversationHistory || [])];
  window.latestWorkflowResult = result;
  if (!isReportTask(window.currentTaskType, getLastUserRequest())) {
    if (queryResult?.answer_text) {
      currentMessages.push(buildMessage("agent", queryResult.answer_text, null, { queryResult }));
    } else if (llm.assistant_message) {
      currentMessages.push(buildMessage("agent", llm.assistant_message));
    } else if (execution?.overview) {
      currentMessages.push(buildMessage("agent", "已完成这次数据查询。你可以继续追问更细的维度，或者明确要求生成正式报告。"));
    }
    if (llm.error) {
      currentMessages.push({
        role: "agent",
        kind: "error_retry",
        text: `模型调用失败：${llm.error}`,
      });
    }
    document.getElementById("conversation-status").textContent = "chat_answered";
    renderArtifactIdle();
  } else if (window.currentStage === STAGE_CLARIFICATION && cards.length > 0) {
    currentMessages.push({
      role: "agent",
      kind: "clarification_group",
      cards
    });
    document.getElementById("conversation-status").textContent = "clarification";
    renderArtifactIdle();
  } else if ((window.currentStage === STAGE_CLARIFICATION && cards.length === 0) || window.currentStage === STAGE_PLAN) {
    window.currentStage = STAGE_PLAN;
    currentMessages.push({
      role: "agent",
      kind: "plan_review",
      steps: plan.steps || []
    });
    document.getElementById("conversation-status").textContent = "plan";
    renderArtifactIdle();
  } else if (window.currentStage === STAGE_REPORT) {
    if (llm.assistant_message) {
      currentMessages.push(buildMessage("agent", llm.assistant_message));
    }
    if (llm.error) {
      currentMessages.push({
        role: "agent",
        kind: "error_retry",
        text: `模型调用失败：${llm.error}`,
      });
    }
    document.getElementById("conversation-status").textContent = "report_ready";
    renderReportFinal(result, plan, execution, llm);
  }

  window.currentMessages = currentMessages;
  replaceConversationWithMessages(currentMessages);
  window.currentCardLookup = Object.fromEntries(cards.map((card) => [card.card_id, card]));
  persistCurrentSessionState();
  renderMessages();
}

async function analyzeFiles() {
  const requestInput = document.getElementById("chat-input");
  const statusText = document.getElementById("status-text");
  const files = window.currentFiles || [];
  const requestText = requestInput.value.trim() || getLastUserRequest();

  if (!files.length) {
    statusText.textContent = "请先选择至少一个 rawdata 文件。";
    persistCurrentSessionState();
    return;
  }

  if (!requestText) {
    statusText.textContent = "请先输入分析需求，或者点击“生成月报”。";
    persistCurrentSessionState();
    return;
  }

  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const taskType = /(月报|报告|复盘|汇报)/.test(requestText) ? "monthly_report" : "question_answering";
  formData.append("task_type", taskType);
  formData.append("user_request", requestText);
  window.currentTaskType = taskType;

  const confirmations = window.currentConfirmations || {};
  const conversationHistory = (window.currentConversationHistory || []).slice(-12).map((item) => ({
    role: item.role,
    text: item.text,
    query_spec: item.querySpec || null,
    query_mode: item.queryResult?.mode || null,
  }));
  (confirmations.reporting_month || []).forEach((month) => formData.append("reporting_month", month));
  if (typeof confirmations.cost_rule_confirmation === "boolean") {
    formData.append("cost_rule_confirmation", String(confirmations.cost_rule_confirmation));
  }
  if (typeof confirmations.free_slot_handling === "boolean") {
    formData.append("free_slot_handling", String(confirmations.free_slot_handling));
  }
  if (confirmations.special_sample_handling) {
    formData.append("special_sample_handling", confirmations.special_sample_handling);
  }
  formData.append("conversation_history", JSON.stringify(conversationHistory));

  statusText.textContent = taskType === "question_answering"
    ? "正在分析并生成回答..."
    : window.currentStage === STAGE_PLAN
    ? "正在生成分析计划..."
    : window.currentStage === STAGE_REPORT
      ? "正在生成最终报告..."
      : "正在生成澄清卡片...";
  persistCurrentSessionState();
  setLoadingState(true);
  try {
    const response = await fetch(apiUrl("/api/analyze"), {
      method: "POST",
      body: formData
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "分析失败");
    }
    statusText.textContent = taskType === "question_answering"
      ? "已完成这次分析回答。"
      : window.currentStage === STAGE_PLAN
      ? "分析计划已生成，请确认。"
      : window.currentStage === STAGE_REPORT
        ? "最终报告已生成。"
        : "请先完成这张澄清卡片。";
    renderWorkflowResult(payload);
    setView("workspace");
  } catch (error) {
    statusText.textContent = error.message === "Failed to fetch"
      ? `分析失败：当前页面没连上本地服务。请直接打开 ${DEFAULT_LOCAL_API_BASE}`
      : `分析失败：${error.message}`;
    window.currentMessages = [
      ...(window.currentConversationHistory || []),
      {
        role: "agent",
        kind: "error_retry",
        text: statusText.textContent,
      }
    ];
    renderMessages();
    persistCurrentSessionState();
  } finally {
    setLoadingState(false);
  }
}

function applyCardAction(cardId, action) {
  window.currentConfirmations = window.currentConfirmations || {};
  let confirmationText = `已确认 ${action}`;
  if (cardId === "reporting_month") {
    const options = window.currentCardLookup?.reporting_month?.options || [];
    if (action === "全部月份") {
      window.currentConfirmations.reporting_month = [...options];
      confirmationText = `本次先看全部月份：${options.join("、")}`;
    } else {
      window.currentConfirmations.reporting_month = [action];
      confirmationText = `本次报告先看 ${action}`;
    }
  } else if (cardId === "cost_rule_confirmation") {
    window.currentConfirmations.cost_rule_confirmation = true;
    confirmationText = "费用口径按当前规则确认";
  } else if (cardId === "free_slot_handling") {
    window.currentConfirmations.free_slot_handling = action === "排除 FREE 成本";
    confirmationText =
      action === "排除 FREE 成本" ? "FREE 点位先排除成本对比" : "FREE 点位先保留成本";
  } else if (cardId === "special_sample_handling") {
    window.currentConfirmations.special_sample_handling =
      action === "尽量排除" ? "exclude_warned_samples" : "keep_warnings_exclude_hard_excludes";
    confirmationText =
      action === "尽量排除" ? "特殊样本先尽量排除" : "特殊样本先保留并标注";
  }
  persistCurrentSessionState();
  renderMessages();
}

function updateFileList() {
  const fileList = document.getElementById("file-list");
  const files = window.currentFiles || [];
  if (!files.length) {
    fileList.innerHTML = '<span class="file-chip muted">还未上传数据文件</span>';
    return;
  }
  fileList.innerHTML = files
    .map((file) => `<span class="file-chip">${file.name}</span>`)
    .join("");
}

function submitCurrentPrompt() {
  const value = document.getElementById("chat-input").value.trim();
  if (!value) {
    return;
  }
  pushConversationMessage("user", value);
  window.currentMessages = [...(window.currentConversationHistory || [])];
  document.getElementById("chat-input").value = "";
  window.currentConfirmations = {};
  window.currentTaskType = /(月报|报告|复盘|汇报)/.test(value) ? "monthly_report" : "question_answering";
  window.currentStage = window.currentTaskType === "monthly_report" ? STAGE_CLARIFICATION : STAGE_CHAT;
  persistCurrentSessionState();
  renderMessages();
  analyzeFiles();
}

document.querySelectorAll(".topbar-actions [data-view]").forEach((button) => {
  button.addEventListener("click", () => {
    setView(button.dataset.view);
  });
});

document.querySelector(".primary-action")?.addEventListener("click", () => {
  persistCurrentSessionState();
  setView("workspace");
  const nextLabel = `新建分析 ${getNextSessionNumber()}`;
  const created = createSessionRecord(nextLabel);
  window.currentSessionId = created.sessionId;
  resetWorkspaceState();
});

document.querySelectorAll(".sidebar-item").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.classList.contains("session-item")) {
      switchSession(button.dataset.sessionId);
      return;
    }
    if (button.classList.contains("agent-item") && button.dataset.agentId && !button.classList.contains("new-agent-entry")) {
      window.currentAgentId = button.dataset.agentId;
      getCurrentSessionState().agentId = button.dataset.agentId;
      updateAgentUI();
      setView("workspace");
      persistCurrentSessionState();
      return;
    }
    if (button.dataset.configModule) {
      setView("config");
      setActiveButton(".sidebar-section .sidebar-item:not(.session-item)", button);
      activateConfigModule(button.dataset.configModule);
      return;
    }
    handleSidebarAction(button);
  });
});

document.getElementById("generate-agent-draft")?.addEventListener("click", () => {
  const input = document.getElementById("agent-builder-input")?.value || "";
  if (!input.trim()) {
    setConfigSaveStatus("请先描述这个智能体");
    return;
  }
  const draft = buildAgentDraftFromNaturalLanguage(input);
  window.configDraft = {
    ...getCurrentConfigDraft(),
    agent_name: draft.name,
    file_types: draft.file_types,
    agent_description: draft.description,
    field_notes: draft.field_notes,
    metric_notes: draft.metric_notes,
    rule_notes: draft.rule_notes,
    clarification_notes: draft.clarification_notes,
    template_notes: draft.template_notes,
    flow_notes: draft.flow_notes,
    assistant_input: draft.assistant_input,
  };
  window.agentCatalog[draft.agent_id] = {
    agent_id: draft.agent_id,
    name: draft.name,
    description: draft.description,
  };
  addAgentToSidebar(window.agentCatalog[draft.agent_id]);
  window.currentAgentId = draft.agent_id;
  getCurrentSessionState().agentId = draft.agent_id;
  renderConfigDraftForm();
  renderAssistantSuggestions(parseAssistantInput(input));
  activateConfigModule("agent-profile");
  updateAgentUI();
  saveConfigDraftToLocal();
  setConfigSaveStatus("agent draft generated");
});

document.querySelectorAll(".module-item").forEach((button) => {
  button.addEventListener("click", () => {
    activateConfigModule(button.dataset.module);
  });
});

document.getElementById("save-config-draft")?.addEventListener("click", () => {
  saveConfigDraftToLocal();
});

document.querySelectorAll(
  "#cfg-agent-name, #cfg-file-types, #cfg-agent-desc, #cfg-field-notes, #cfg-metric-notes, #cfg-rule-notes, #cfg-clarification-notes, #cfg-template-notes, #cfg-flow-notes, #assistant-input-preview"
).forEach((element) => {
  element.addEventListener("input", () => {
    collectConfigDraftFromForm();
    setConfigSaveStatus("editing...");
  });
});

document.getElementById("assistant-parse-btn")?.addEventListener("click", () => {
  const input = document.getElementById("assistant-input-preview")?.value || "";
  const suggestions = parseAssistantInput(input);
  renderAssistantSuggestions(suggestions);
  collectConfigDraftFromForm();
  setConfigSaveStatus("parsed");
});

document.getElementById("assistant-apply-btn")?.addEventListener("click", () => {
  const input = document.getElementById("assistant-input-preview")?.value || "";
  const suggestions = parseAssistantInput(input);
  renderAssistantSuggestions(suggestions);

  const ruleBox = document.getElementById("cfg-rule-notes");
  const flowBox = document.getElementById("cfg-flow-notes");
  const clarificationBox = document.getElementById("cfg-clarification-notes");
  if (ruleBox) {
    ruleBox.value = `${ruleBox.value ? `${ruleBox.value}\n` : ""}${suggestions.filter((item) => item.includes("规则")).join("\n")}`.trim();
  }
  if (flowBox && suggestions.some((item) => item.includes("流程"))) {
    flowBox.value = `${flowBox.value ? `${flowBox.value}\n` : ""}${suggestions.filter((item) => item.includes("流程")).join("\n")}`.trim();
  }
  if (clarificationBox && input.includes("确认")) {
    clarificationBox.value = `${clarificationBox.value ? `${clarificationBox.value}\n` : ""}新增澄清：${input}`.trim();
  }
  saveConfigDraftToLocal();
  setConfigSaveStatus("applied");
});

document.getElementById("send-button").addEventListener("click", submitCurrentPrompt);
document.getElementById("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitCurrentPrompt();
  }
});
document.getElementById("chat-input").addEventListener("input", (event) => {
  const state = getCurrentSessionState();
  state.draftInput = event.target.value;
});
document.getElementById("file-input").addEventListener("change", (event) => {
  window.currentFiles = Array.from(event.target.files || []);
  persistCurrentSessionState();
  updateFileList();
});
document.querySelectorAll(".action-chip").forEach((button) => {
  button.addEventListener("click", () => {
    document.getElementById("chat-input").value = button.dataset.prompt;
    persistCurrentSessionState();
    submitCurrentPrompt();
  });
});
document.getElementById("message-stream").addEventListener("click", (event) => {
  const stageTarget = event.target.closest("[data-stage-action]");
  if (stageTarget) {
    if (stageTarget.dataset.stageAction === "confirm-clarifications") {
      window.currentStage = STAGE_PLAN;
      analyzeFiles();
      return;
    }
    if (stageTarget.dataset.stageAction === "confirm-plan") {
      window.currentStage = STAGE_REPORT;
      renderWorkflowResult(window.latestWorkflowResult || {});
      return;
    }
  }
  const target = event.target.closest(".chip-button[data-card-id]");
  const retryTarget = event.target.closest("[data-retry-analysis]");
  const queryClarificationTarget = event.target.closest("[data-query-clarification]");
  const queryFollowupTarget = event.target.closest("[data-query-followup]");
  if (retryTarget) {
    analyzeFiles();
    return;
  }
  if (queryClarificationTarget) {
    const followUpText = queryClarificationTarget.dataset.queryClarification;
    pushConversationMessage("user", followUpText);
    window.currentMessages = [...(window.currentConversationHistory || [])];
    document.getElementById("chat-input").value = "";
    persistCurrentSessionState();
    renderMessages();
    analyzeFiles();
    return;
  }
  if (queryFollowupTarget) {
    const followUpText = queryFollowupTarget.dataset.queryFollowup;
    pushConversationMessage("user", followUpText);
    window.currentMessages = [...(window.currentConversationHistory || [])];
    document.getElementById("chat-input").value = "";
    persistCurrentSessionState();
    renderMessages();
    analyzeFiles();
    return;
  }
  if (!target) {
    return;
  }
  applyCardAction(target.dataset.cardId, target.dataset.action);
});

ensureSessionStore();
setView("workspace");
syncWindowStateFromSession(window.currentSessionId);
const versionElement = document.getElementById("app-version");
if (versionElement) {
  versionElement.textContent = APP_VERSION;
}
if (window.location.protocol === "file:") {
  document.getElementById("status-text").textContent = `当前是本地文件预览模式，分析与配置会自动连接 ${DEFAULT_LOCAL_API_BASE}。`;
  persistCurrentSessionState();
}
loadConfigStudio();
