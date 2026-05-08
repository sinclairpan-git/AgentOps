export const TermGlossary = {
  name: "TermGlossary",
  props: {
    terms: { type: Array, required: true }
  },
  template: `
    <section v-if="terms.length" class="term-glossary" aria-label="术语说明">
      <div v-for="term in terms" :key="term.label" class="term-chip">
        <strong>{{ term.label }}</strong>
        <span>{{ term.copy }}</span>
      </div>
    </section>
  `
};
