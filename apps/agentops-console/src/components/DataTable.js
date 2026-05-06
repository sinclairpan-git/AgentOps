import { StatusBadge } from "./StatusBadge.js";

export const DataTable = {
  name: "DataTable",
  components: {
    StatusBadge
  },
  props: {
    columns: { type: Array, required: true },
    rows: { type: Array, required: true },
    rowActionLabel: { type: String, default: "" }
  },
  template: `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
            <th v-if="rowActionLabel">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id || row.run_id || row.approval_id || row.evidence_id">
            <td v-for="column in columns" :key="column.key" :data-label="column.label">
              <status-badge v-if="column.type === 'status'" :status="row[column.key]" />
              <span v-else>{{ row[column.key] }}</span>
            </td>
            <td v-if="rowActionLabel" data-label="操作">
              <button class="table-action" type="button" @click="$emit('row-action', row)">{{ rowActionLabel }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `
};
