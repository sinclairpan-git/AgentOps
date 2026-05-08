import { StatusBadge } from "./StatusBadge.js";

export const AppShell = {
  name: "AppShell",
  components: {
    StatusBadge
  },
  props: {
    routes: { type: Array, required: true },
    activeRoute: { type: String, required: true },
    summary: { type: Object, required: true },
    operationCenter: { type: Object, required: true },
    actionWorkbench: { type: Object, required: true },
    activeActionId: { type: String, default: "" },
    sourceState: { type: Object, required: true },
    showSourceBanner: { type: Boolean, default: true }
  },
  data() {
    return {
      menuOpen: false,
      notificationOpen: false,
      todoOpen: false,
      searchQuery: ""
    };
  },
  computed: {
    activeLabel() {
      const active = this.routes.find((route) => route.id === this.activeRoute);
      return active ? active.label : "总览";
    },
    notifications() {
      return Array.isArray(this.operationCenter.notifications) ? this.operationCenter.notifications : [];
    },
    todos() {
      return Array.isArray(this.operationCenter.todos) ? this.operationCenter.todos : [];
    },
    searchIndex() {
      return Array.isArray(this.operationCenter.searchIndex) ? this.operationCenter.searchIndex : [];
    },
    routeSearchIndex() {
      return this.routes
        .filter((route) => route.id !== this.activeRoute)
        .map((route) => ({
          id: route.label,
          kind: "页面",
          title: `打开${route.label}`,
          status: route.id === "risks" ? "warning" : "healthy",
          route: route.id
        }));
    },
    combinedSearchIndex() {
      const seen = new Set();
      return [...this.searchIndex, ...this.routeSearchIndex].filter((item) => {
        const key = `${item.route}:${item.id}`;
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      });
    },
    searchHasQuery() {
      return Boolean(this.searchQuery.trim());
    },
    actionDetails() {
      return Array.isArray(this.actionWorkbench.details) ? this.actionWorkbench.details : [];
    },
    activeActionDetail() {
      return this.actionDetails.find((item) => item.id === this.activeActionId) || null;
    },
    searchResults() {
      const query = this.searchQuery.trim().toLowerCase();
      if (!query) {
        return [];
      }
      return this.combinedSearchIndex
        .filter((item) => `${item.id} ${item.kind} ${item.title} ${item.status} ${this.routeLabel(item.route)}`.toLowerCase().includes(query))
        .slice(0, 6);
    }
  },
  methods: {
    displayValue(value) {
      return String(value ?? "")
        .replaceAll("verified_loaded", "已验证加载")
        .replaceAll("materialized/unverified", "已生成配置/未验证")
        .replaceAll("materialized", "已生成配置")
        .replaceAll("unverified", "未验证")
        .replaceAll("require_online", "在线校验")
        .replaceAll("Grant", "授权票")
        .replaceAll("TTL", "有效期")
        .replaceAll("DLQ", "异常队列")
        .replaceAll("Outbox Replay", "事件重放")
        .replaceAll("Outbox delivered", "事件已投递")
        .replaceAll("Outbox", "事件投递箱")
        .replaceAll("ReporterCredential", "上报器凭证")
        .replaceAll("Reporter", "上报器")
        .replaceAll("IngestionToken", "接入令牌")
        .replaceAll("DeviceKey", "设备密钥");
    },
    routeLabel(routeId) {
      const route = this.routes.find((candidate) => candidate.id === routeId);
      return route ? route.label : "目标视图";
    },
    closeOperationPanels() {
      this.notificationOpen = false;
      this.todoOpen = false;
    },
    toggleNotifications() {
      this.searchQuery = "";
      this.notificationOpen = !this.notificationOpen;
      this.todoOpen = false;
    },
    toggleTodos() {
      this.searchQuery = "";
      this.todoOpen = !this.todoOpen;
      this.notificationOpen = false;
    },
    choose(routeId) {
      this.menuOpen = false;
      this.notificationOpen = false;
      this.todoOpen = false;
      this.searchQuery = "";
      this.$emit("close-action-detail");
      this.$emit("navigate", routeId);
    },
    chooseSearchResult(item) {
      this.openOperationItem(item);
    },
    openOperationItem(item) {
      this.menuOpen = false;
      this.notificationOpen = false;
      this.todoOpen = false;
      this.searchQuery = "";
      this.$emit("navigate", item.route);
      if (item.action_id) {
        this.$emit("open-action-detail", item.action_id);
      } else {
        this.$emit("close-action-detail");
      }
    }
  },
  template: `
    <div class="console-shell">
      <aside class="sidebar" :class="{ 'sidebar--open': menuOpen }" aria-label="AgentOps 导航">
        <div class="brand">
          <div class="brand-mark">AO</div>
          <div>
            <h1>AgentOps</h1>
            <p>治理控制台</p>
          </div>
        </div>
        <nav class="nav-list">
          <button
            v-for="route in routes"
            :key="route.id"
            class="nav-item"
            :class="{ 'nav-item--active': route.id === activeRoute }"
            type="button"
            @click="choose(route.id)"
          >
            <span class="nav-icon" aria-hidden="true">{{ route.icon }}</span>
            <span>{{ route.label }}</span>
          </button>
        </nav>
      </aside>

      <main class="workspace">
        <header class="topbar">
          <button class="menu-button" type="button" aria-label="展开或收起导航" @click="menuOpen = !menuOpen">
            <span aria-hidden="true">☰</span>
            <span class="menu-button-label">菜单</span>
          </button>
          <div class="topbar-title">
            <p class="eyebrow">当前视图</p>
            <h2>{{ activeLabel }}</h2>
          </div>
          <div class="global-search">
            <label class="sr-only" for="agentops-global-search">全局搜索</label>
            <input
              id="agentops-global-search"
              v-model="searchQuery"
              type="search"
              placeholder="搜索运行、证据、审批、风险"
              @focus="closeOperationPanels"
              @input="closeOperationPanels"
            />
            <div v-if="searchHasQuery" class="search-results">
              <template v-if="searchResults.length">
                <button
                  v-for="item in searchResults"
                  :key="item.id"
                  type="button"
                  class="search-result"
                  @click="chooseSearchResult(item)"
                >
                  <span>{{ item.kind }}</span>
                  <strong>{{ item.id }}</strong>
                  <small>{{ displayValue(item.title) }}</small>
                  <status-badge :status="item.status" />
                  <small class="search-route">去往：{{ routeLabel(item.route) }}</small>
                </button>
              </template>
              <div v-else class="search-empty">
                <strong>未找到匹配结果</strong>
                <small>换一个关键词，或从左侧导航进入对应工作台。</small>
              </div>
            </div>
          </div>
          <div class="topbar-status">
            <status-badge :status="summary.adapter.status" />
            <span class="proof-copy">{{ displayValue(summary.adapter.copy) }}</span>
          </div>
          <div class="topbar-actions">
            <button class="ops-button" type="button" @click="toggleNotifications">
              通知 <strong>{{ notifications.length }}</strong>
            </button>
            <button class="ops-button" type="button" @click="toggleTodos">
              待办 <strong>{{ todos.length }}</strong>
            </button>
          </div>
        </header>
        <section v-if="notificationOpen" class="ops-panel">
          <div class="section-title">
            <h4>通知中心</h4>
            <span>治理变化和异常提醒</span>
          </div>
          <button v-for="item in notifications" :key="item.id" type="button" class="ops-row" @click="openOperationItem(item)">
            <span>
              <strong>{{ displayValue(item.title) }}</strong>
              <small>{{ displayValue(item.body) }}</small>
            </span>
            <status-badge :status="item.status" />
          </button>
          <p v-if="!notifications.length" class="empty-state">暂无通知。</p>
        </section>
        <section v-if="todoOpen" class="ops-panel">
          <div class="section-title">
            <h4>待办中心</h4>
            <span>按负责人和到期线处理</span>
          </div>
          <button v-for="item in todos" :key="item.id" type="button" class="ops-row" @click="openOperationItem(item)">
            <span>
              <strong>{{ displayValue(item.title) }}</strong>
              <small>{{ item.owner }} / {{ item.due }}</small>
              <small>{{ displayValue(item.body) }}</small>
            </span>
            <status-badge :status="item.status" />
          </button>
          <p v-if="!todos.length" class="empty-state">暂无待办。</p>
        </section>
        <section v-if="showSourceBanner" class="source-banner" :class="'source-banner--' + sourceState.status">
          <status-badge :status="sourceState.status" />
          <div>
            <strong>{{ sourceState.label }}</strong>
            <p>{{ displayValue(sourceState.copy) }}</p>
            <dl class="source-meta">
              <div>
                <dt>生成时间</dt>
                <dd>{{ sourceState.generatedAt }}</dd>
              </div>
              <div>
                <dt>来源类型</dt>
                <dd>{{ sourceState.sourceType }}</dd>
              </div>
              <div>
                <dt>来源边界</dt>
                <dd>{{ sourceState.sourceSummary }}</dd>
              </div>
            </dl>
            <div class="source-actions">
              <small>{{ sourceState.request_id }}</small>
              <button class="ent-button ent-button--secondary source-action" type="button" @click="$emit('refresh-snapshot')">
                {{ sourceState.primary_action }}
              </button>
            </div>
          </div>
        </section>
        <section class="content-region">
          <slot />
        </section>
      </main>
      <aside v-if="activeActionDetail" class="action-drawer" aria-label="处置详情">
        <div class="action-drawer-header">
          <div>
            <p class="eyebrow">处置详情</p>
            <h3>{{ displayValue(activeActionDetail.title) }}</h3>
          </div>
          <button class="icon-button" type="button" aria-label="关闭处置详情" @click="$emit('close-action-detail')">×</button>
        </div>
        <status-badge :status="activeActionDetail.status" />
        <p class="summary-copy">{{ displayValue(activeActionDetail.summary) }}</p>
        <dl class="detail-list action-detail-list">
          <div><dt>负责人</dt><dd>{{ activeActionDetail.owner }}</dd></div>
          <div><dt>建议动作</dt><dd>{{ displayValue(activeActionDetail.primary_action) }}</dd></div>
          <div><dt>备用动作</dt><dd>{{ displayValue(activeActionDetail.secondary_action) }}</dd></div>
          <div><dt>关闭条件</dt><dd>{{ displayValue(activeActionDetail.close_condition) }}</dd></div>
          <div><dt>审计引用</dt><dd>{{ activeActionDetail.audit_ref }}</dd></div>
          <div v-if="activeActionDetail.evidence_ref"><dt>证据引用</dt><dd>{{ activeActionDetail.evidence_ref }}</dd></div>
          <div v-if="activeActionDetail.related_ref"><dt>关联对象</dt><dd>{{ activeActionDetail.related_ref }}</dd></div>
        </dl>
        <section v-if="activeActionDetail.timeline && activeActionDetail.timeline.length" class="timeline-section">
          <div class="section-title">
            <h4>处置时间线</h4>
            <span>只读进展</span>
          </div>
          <ol class="timeline-list">
            <li v-for="node in activeActionDetail.timeline" :key="node.id" class="timeline-node">
              <div class="timeline-marker" aria-hidden="true"></div>
              <div>
                <div class="timeline-head">
                  <strong>{{ node.stage }}：{{ node.title }}</strong>
                  <status-badge :status="node.status" />
                </div>
                <p>{{ displayValue(node.body) }}</p>
                <small>{{ node.occurred_at }} / {{ node.owner }}</small>
              </div>
            </li>
          </ol>
        </section>
        <section v-if="activeActionDetail.audit_packet" class="audit-packet">
          <div class="section-title">
            <h4>审计包摘要</h4>
            <span>只读复核包</span>
          </div>
          <p>{{ displayValue(activeActionDetail.audit_packet.summary) }}</p>
          <dl class="detail-list">
            <div><dt>导出状态</dt><dd>{{ activeActionDetail.audit_packet.export_state }}</dd></div>
            <div><dt>回显目标</dt><dd>{{ activeActionDetail.audit_packet.echo_targets.join('、') }}</dd></div>
            <div><dt>证据引用</dt><dd>{{ activeActionDetail.audit_packet.evidence_refs.join('、') }}</dd></div>
            <div><dt>保留策略</dt><dd>{{ displayValue(activeActionDetail.audit_packet.retention_policy) }}</dd></div>
          </dl>
          <p class="safety-note">{{ displayValue(activeActionDetail.audit_packet.safety_note) }}</p>
        </section>
        <p class="safety-note">{{ displayValue(activeActionDetail.safety_note) }}</p>
        <div class="action-drawer-actions">
          <button class="ent-button" type="button" @click="choose(activeActionDetail.route)">前往相关页面</button>
          <span class="readonly-action-note">建议动作，不在本页执行：{{ displayValue(activeActionDetail.primary_action) }}</span>
        </div>
      </aside>
    </div>
  `
};
