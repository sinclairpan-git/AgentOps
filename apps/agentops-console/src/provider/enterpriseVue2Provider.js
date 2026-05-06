export const ENTERPRISE_VUE2_PROVIDER = {
  name: "sdlc-enterprise-vue2",
  packageName: "@sxf/er-components",
  installedVersion: "1.27.5",
  sourcePath: "vendor/enterprise-vue2/sxf-er-components-1.27.5.tgz",
  themePackageName: "@sxf/sf-theme",
  themeInstalledVersion: "0.2.5",
  themeSourcePath: "vendor/enterprise-vue2/sxf-sf-theme-0.2.5.tgz",
  frameworkBaseline: "/Users/sinclairpan/project/Ai_AutoSDLC/specs/016-frontend-enterprise-vue2-provider-baseline/spec.md",
  allowFullVueUse: false,
  allowedCapabilities: [
    "UiButton",
    "UiCard",
    "UiTag",
    "UiTabs",
    "UiDrawer",
    "UiMenu",
    "UiToolbar",
    "UiPagination",
    "UiGrid"
  ]
};

const EntButton = {
  name: "EntButton",
  props: {
    tone: { type: String, default: "default" },
    type: { type: String, default: "button" }
  },
  template: `
    <button class="ent-button" :class="'ent-button--' + tone" :type="type" @click="$emit('click', $event)">
      <slot />
    </button>
  `
};

const EntCard = {
  name: "EntCard",
  props: {
    dense: { type: Boolean, default: false }
  },
  template: `
    <section class="ent-card" :class="{ 'ent-card--dense': dense }">
      <slot />
    </section>
  `
};

const EntToolbar = {
  name: "EntToolbar",
  template: `
    <div class="ent-toolbar">
      <slot />
    </div>
  `
};

const EntTabs = {
  name: "EntTabs",
  props: {
    items: { type: Array, required: true },
    value: { type: String, required: true }
  },
  template: `
    <div class="ent-tabs" role="tablist">
      <button
        v-for="item in items"
        :key="item.id"
        class="ent-tab"
        :class="{ 'ent-tab--active': item.id === value }"
        type="button"
        role="tab"
        :aria-selected="item.id === value ? 'true' : 'false'"
        @click="$emit('input', item.id)"
      >
        {{ item.label }}
      </button>
    </div>
  `
};

export const EnterpriseVue2Provider = {
  install(Vue) {
    Vue.component("EntButton", EntButton);
    Vue.component("EntCard", EntCard);
    Vue.component("EntToolbar", EntToolbar);
    Vue.component("EntTabs", EntTabs);
  }
};
