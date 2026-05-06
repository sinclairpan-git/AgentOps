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
    sourceState: { type: Object, required: true }
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
    searchResults() {
      const query = this.searchQuery.trim().toLowerCase();
      if (!query) {
        return [];
      }
      return this.searchIndex
        .filter((item) => `${item.id} ${item.kind} ${item.title} ${item.status}`.toLowerCase().includes(query))
        .slice(0, 6);
    }
  },
  methods: {
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
      this.$emit("navigate", routeId);
    },
    chooseSearchResult(item) {
      this.searchQuery = "";
      this.choose(item.route);
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
          <button class="menu-button" type="button" aria-label="展开或收起导航" @click="menuOpen = !menuOpen">☰</button>
          <div>
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
            <div v-if="searchResults.length" class="search-results">
              <button
                v-for="item in searchResults"
                :key="item.id"
                type="button"
                class="search-result"
                @click="chooseSearchResult(item)"
              >
                <span>{{ item.kind }}</span>
                <strong>{{ item.id }}</strong>
                <small>{{ item.title }}</small>
                <status-badge :status="item.status" />
                <small class="search-route">去往：{{ routeLabel(item.route) }}</small>
              </button>
            </div>
          </div>
          <div class="topbar-status">
            <status-badge :status="summary.adapter.status" />
            <span class="proof-copy">{{ summary.adapter.copy }}</span>
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
          <button v-for="item in notifications" :key="item.id" type="button" class="ops-row" @click="choose(item.route)">
            <span>
              <strong>{{ item.title }}</strong>
              <small>{{ item.body }}</small>
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
          <button v-for="item in todos" :key="item.id" type="button" class="ops-row" @click="choose(item.route)">
            <span>
              <strong>{{ item.title }}</strong>
              <small>{{ item.owner }} / {{ item.due }}</small>
              <small>{{ item.body }}</small>
            </span>
            <status-badge :status="item.status" />
          </button>
          <p v-if="!todos.length" class="empty-state">暂无待办。</p>
        </section>
        <section class="source-banner" :class="'source-banner--' + sourceState.status">
          <status-badge :status="sourceState.status" />
          <div>
            <strong>{{ sourceState.label }}</strong>
            <p>{{ sourceState.copy }}</p>
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
    </div>
  `
};
