import { StatusBadge } from "./StatusBadge.js";

export const AppShell = {
  name: "AppShell",
  components: {
    StatusBadge
  },
  props: {
    routes: { type: Array, required: true },
    activeRoute: { type: String, required: true },
    summary: { type: Object, required: true }
  },
  data() {
    return {
      menuOpen: false
    };
  },
  computed: {
    activeLabel() {
      const active = this.routes.find((route) => route.id === this.activeRoute);
      return active ? active.label : "总览";
    }
  },
  methods: {
    choose(routeId) {
      this.menuOpen = false;
      this.$emit("navigate", routeId);
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
          <div class="topbar-status">
            <status-badge :status="summary.adapter.status" />
            <span class="proof-copy">{{ summary.adapter.copy }}</span>
          </div>
        </header>
        <section class="content-region">
          <slot />
        </section>
      </main>
    </div>
  `
};
