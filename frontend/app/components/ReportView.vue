<script setup lang="ts">
import type { AgentOutput } from '~/types'

defineProps<{ report: AgentOutput }>()

const expanded = ref<Set<string>>(new Set())
const toggle = (key: string) => {
  expanded.value.has(key) ? expanded.value.delete(key) : expanded.value.add(key)
}

const relMeta = (r: string) =>
  ({ high: { label: 'High', cls: 'rel-high' }, medium: { label: 'Med', cls: 'rel-med' }, low: { label: 'Low', cls: 'rel-low' } }[r]
    ?? { label: r, cls: 'rel-low' })
</script>

<template>
  <article class="report">
    <!-- Title + Summary -->
    <header class="r-header">
      <h1 class="r-title">{{ report.title }}</h1>
      <p class="r-summary">{{ report.summary }}</p>
    </header>

    <!-- Key Findings -->
    <section class="r-section">
      <h2 class="r-h2">Key Findings</h2>
      <ol class="findings">
        <li v-for="(f, i) in report.key_findings" :key="i" class="finding">
          <span class="f-num">{{ i + 1 }}</span>
          <span class="f-text">{{ f }}</span>
        </li>
      </ol>
    </section>

    <!-- Analysis Sections (accordion) -->
    <section v-if="Object.keys(report.sections).length" class="r-section">
      <h2 class="r-h2">Analysis</h2>
      <div class="accordion">
        <div
          v-for="[key, body] in Object.entries(report.sections)"
          :key="key"
          class="acc-item"
          :class="{ open: expanded.has(key) }"
        >
          <button class="acc-trigger" @click="toggle(key)">
            <span class="acc-key">{{ key }}</span>
            <span class="acc-chevron">{{ expanded.has(key) ? '▲' : '▼' }}</span>
          </button>
          <div v-show="expanded.has(key)" class="acc-body">{{ body }}</div>
        </div>
      </div>
    </section>

    <!-- Sources -->
    <section v-if="report.sources.length" class="r-section">
      <h2 class="r-h2">Sources <span class="r-count">({{ report.sources.length }})</span></h2>
      <div class="sources-grid">
        <a
          v-for="src in report.sources"
          :key="src.url"
          :href="src.url"
          target="_blank"
          rel="noopener noreferrer"
          class="source-card"
        >
          <span :class="['rel-badge', relMeta(src.relevance).cls]">
            {{ relMeta(src.relevance).label }}
          </span>
          <span class="src-title">{{ src.title }}</span>
          <span class="src-url">{{ src.url }}</span>
        </a>
      </div>
    </section>

    <!-- Limitations -->
    <section v-if="report.limitations" class="r-section">
      <h2 class="r-h2">Limitations</h2>
      <div class="limits-box">{{ report.limitations }}</div>
    </section>
  </article>
</template>

<style scoped>
.report {
  display: flex;
  flex-direction: column;
  gap: 28px;
  animation: fade-in 0.3s ease;
}

/* Header */
.r-header {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px 28px;
}

.r-title {
  font-size: clamp(18px, 2.5vw, 26px);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text);
  margin-bottom: 10px;
}

.r-summary {
  font-size: 15px;
  color: var(--muted);
  line-height: 1.65;
}

/* Section base */
.r-section { display: flex; flex-direction: column; gap: 12px; }

.r-h2 {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 6px;
}

.r-count { font-weight: 400; color: var(--faint); }

/* Findings */
.findings { display: flex; flex-direction: column; gap: 8px; list-style: none; }

.finding {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 13px 16px;
}

.f-num {
  width: 22px;
  height: 22px;
  background: var(--indigo-l);
  color: var(--indigo-d);
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.f-text { font-size: 14px; line-height: 1.6; color: var(--text); }

/* Accordion */
.accordion { display: flex; flex-direction: column; gap: 4px; }

.acc-item {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 9px;
  overflow: hidden;
  transition: border-color 0.15s;
}
.acc-item.open { border-color: var(--indigo); }

.acc-trigger {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  text-align: left;
}
.acc-trigger:hover { background: #FAFBFC; }

.acc-chevron { font-size: 9px; color: var(--faint); transition: color 0.14s; }
.acc-item.open .acc-chevron { color: var(--indigo); }

.acc-body {
  padding: 2px 16px 14px;
  font-size: 13.5px;
  color: var(--muted);
  line-height: 1.7;
  border-top: 1px solid var(--border);
  white-space: pre-wrap;
}

/* Sources */
.sources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}

.source-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 13px 15px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 9px;
  transition: border-color 0.14s, box-shadow 0.14s;
  cursor: pointer;
}
.source-card:hover {
  border-color: var(--indigo);
  box-shadow: 0 2px 8px rgba(99,102,241,0.12);
}

.rel-badge {
  align-self: flex-start;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 600;
}
.rel-high { background: #DCFCE7; color: #15803D; }
.rel-med  { background: #FEF9C3; color: #854D0E; }
.rel-low  { background: #F1F5F9; color: var(--muted); }

.src-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.src-url {
  font-size: 11px;
  color: var(--faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Limitations */
.limits-box {
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  border-radius: 9px;
  padding: 14px 16px;
  font-size: 13.5px;
  color: #92400E;
  line-height: 1.65;
}
</style>
