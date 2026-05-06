import { AppShell } from "./components/AppShell.js";
import { consoleData, routes } from "./data/mockAgentOpsData.js";
import { OverviewView } from "./views/OverviewView.js";
import { RunsView } from "./views/RunsView.js";
import { EvidenceExplorerView } from "./views/EvidenceExplorerView.js";
import { ApprovalCenterView } from "./views/ApprovalCenterView.js";
import { PolicyCenterView } from "./views/PolicyCenterView.js";
import { QualityCenterView } from "./views/QualityCenterView.js";
import { RiskTriageView } from "./views/RiskTriageView.js";
import { ConnectorStatusView } from "./views/ConnectorStatusView.js";
import { SdlcRunsView } from "./views/SdlcRunsView.js";

const views = {
  overview: OverviewView,
  runs: RunsView,
  evidence: EvidenceExplorerView,
  approvals: ApprovalCenterView,
  policies: PolicyCenterView,
  quality: QualityCenterView,
  risks: RiskTriageView,
  connectors: ConnectorStatusView,
  "sdlc-runs": SdlcRunsView
};

export default {
  name: "AgentOpsConsole",
  components: {
    AppShell
  },
  data() {
    return {
      activeRoute: "overview",
      routes,
      consoleData
    };
  },
  computed: {
    activeView() {
      return views[this.activeRoute] || OverviewView;
    }
  },
  methods: {
    navigate(routeId) {
      this.activeRoute = routeId;
    }
  },
  template: `
    <app-shell
      :routes="routes"
      :active-route="activeRoute"
      :summary="consoleData.summary"
      @navigate="navigate"
    >
      <component
        :is="activeView"
        :data="consoleData"
        :active-route="activeRoute"
        @navigate="navigate"
      />
    </app-shell>
  `
};
