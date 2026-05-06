import { StatusBadge } from "./StatusBadge.js";

export const MetricTile = {
  name: "MetricTile",
  components: {
    StatusBadge
  },
  props: {
    label: { type: String, required: true },
    value: { type: [String, Number], required: true },
    status: { type: String, required: true },
    detail: { type: String, default: "" }
  },
  template: `
    <ent-card dense>
      <div class="metric-tile">
        <div>
          <p class="metric-label">{{ label }}</p>
          <strong>{{ value }}</strong>
        </div>
        <status-badge :status="status" />
      </div>
      <p v-if="detail" class="muted">{{ detail }}</p>
    </ent-card>
  `
};
