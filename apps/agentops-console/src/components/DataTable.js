import { StatusBadge } from "./StatusBadge.js";

export const DataTable = {
  name: "DataTable",
  components: {
    StatusBadge
  },
  props: {
    columns: { type: Array, required: true },
    rows: { type: Array, required: true }
  },
  template: `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id || row.run_id || row.approval_id || row.evidence_id">
            <td v-for="column in columns" :key="column.key" :data-label="column.label">
              <status-badge v-if="column.type === 'status'" :status="row[column.key]" />
              <span v-else>{{ row[column.key] }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `
};
