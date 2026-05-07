import { AppShell } from "./components/AppShell.js";
import { initialSnapshot, loadAgentOpsSnapshot } from "./data/agentOpsApiClient.js";
import { OverviewView } from "./views/OverviewView.js";
import { RunsView } from "./views/RunsView.js";
import { EvidenceExplorerView } from "./views/EvidenceExplorerView.js";
import { ApprovalCenterView } from "./views/ApprovalCenterView.js";
import { PolicyCenterView } from "./views/PolicyCenterView.js";
import { QualityCenterView } from "./views/QualityCenterView.js";
import { RiskTriageView } from "./views/RiskTriageView.js";
import { AgentStoreAuditView } from "./views/AgentStoreAuditView.js";
import { CredentialHandoffView } from "./views/CredentialHandoffView.js";
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
  "agent-store-audit": AgentStoreAuditView,
  "credential-handoff": CredentialHandoffView,
  connectors: ConnectorStatusView,
  "sdlc-runs": SdlcRunsView
};

export default {
  name: "AgentOpsConsole",
  components: {
    AppShell
  },
  data() {
    const snapshot = initialSnapshot();
    return {
      activeRoute: "overview",
      routes: snapshot.routes,
      consoleData: snapshot.consoleData,
      sourceState: snapshot.sourceState,
      activeActionId: ""
    };
  },
  async mounted() {
    await this.refreshSnapshot();
  },
  methods: {
    async refreshSnapshot() {
      const loading = initialSnapshot();
      this.sourceState = loading.sourceState;
      const snapshot = await loadAgentOpsSnapshot();
      this.routes = snapshot.routes;
      this.consoleData = snapshot.consoleData;
      this.sourceState = snapshot.sourceState;
    },
    navigate(routeId) {
      this.activeRoute = routeId;
    },
    openActionDetail(actionId) {
      this.activeActionId = actionId;
    },
    closeActionDetail() {
      this.activeActionId = "";
    }
  },
  computed: {
    activeView() {
      return views[this.activeRoute] || OverviewView;
    }
  },
  template: `
    <app-shell
      :routes="routes"
      :active-route="activeRoute"
      :summary="consoleData.summary"
      :operation-center="consoleData.operationCenter"
      :action-workbench="consoleData.actionWorkbench"
      :active-action-id="activeActionId"
      :source-state="sourceState"
      @navigate="navigate"
      @open-action-detail="openActionDetail"
      @close-action-detail="closeActionDetail"
      @refresh-snapshot="refreshSnapshot"
    >
      <component
        :is="activeView"
        :data="consoleData"
        :active-route="activeRoute"
        @navigate="navigate"
        @open-action-detail="openActionDetail"
      />
    </app-shell>
  `
};
