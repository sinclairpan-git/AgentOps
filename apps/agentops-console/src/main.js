import Vue from "vue";
import App from "./App.js";
import { EnterpriseVue2Provider } from "./provider/enterpriseVue2Provider.js";
import "./styles.css";

Vue.config.productionTip = false;
Vue.use(EnterpriseVue2Provider);

new Vue({
  render: (h) => h(App)
}).$mount("#app");
