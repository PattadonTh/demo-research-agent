<script setup lang="ts">
import type { TaskStatus } from '~/types'

const api = useResearchApi()
const route = useRoute()
const history = ref<TaskStatus[]>([])

const loadHistory = async () => {
  try {
    history.value = await api.getHistory()
  } catch {}
}

onMounted(loadHistory)
watch(() => route.path, loadHistory)

const formatDate = (iso: string) => {
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 60_000) return 'just now'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`
  return new Date(iso).toLocaleDateString()
}

const statusMeta: Record<string, { icon: string; cls: string }> = {
  running:        { icon: '⟳', cls: 'running' },
  waiting_review: { icon: '◈', cls: 'review' },
  completed:      { icon: '✓', cls: 'done' },
  failed:         { icon: '✕', cls: 'fail' },
}
</script>

<template>
  <div class="layout">
    <NuxtRouteAnnouncer />

    <aside class="sidebar">
      <div class="sidebar-logo">
        <span class="logo-hex">⬡</span>
        <span class="logo-name">ResearchAgent</span>
      </div>

      <NuxtLink to="/" class="new-btn">
        <span>＋</span> New Research
      </NuxtLink>

      <nav class="history-nav">
        <div class="nav-label">Recent</div>
        <template v-if="history.length > 0">
          <NuxtLink
            v-for="item in history.slice(0, 25)"
            :key="item.thread_id"
            :to="`/task/${item.thread_id}`"
            class="history-item"
            :class="[statusMeta[item.status]?.cls, { active: route.params.id === item.thread_id }]"
          >
            <span class="h-icon">{{ statusMeta[item.status]?.icon }}</span>
            <div class="h-body">
              <span class="h-task">{{ item.task }}</span>
              <span class="h-date">{{ formatDate(item.created_at) }}</span>
            </div>
          </NuxtLink>
        </template>
        <p v-else class="no-history">No research yet</p>
      </nav>
    </aside>

    <main class="main">
      <NuxtPage @history-updated="loadHistory" />
    </main>
  </div>
</template>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --sw: 252px;
  --indigo: #6366F1;
  --indigo-d: #4F46E5;
  --indigo-l: #EEF2FF;
  --bg: #F1F5F9;
  --card: #FFFFFF;
  --border: #E2E8F0;
  --text: #0F172A;
  --muted: #64748B;
  --faint: #94A3B8;
  --green: #22C55E;
  --amber: #F59E0B;
  --red: #EF4444;
  --blue: #3B82F6;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
}

body {
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a { text-decoration: none; color: inherit; }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:.4 } }
@keyframes fade-in { from { opacity:0; transform:translateY(6px) } to { opacity:1; transform:none } }
</style>

<style scoped>
.layout { display: flex; min-height: 100vh; }

.sidebar {
  width: var(--sw);
  background: #0F172A;
  color: #CBD5E1;
  display: flex;
  flex-direction: column;
  padding: 18px 12px;
  position: fixed;
  inset: 0 auto 0 0;
  overflow-y: auto;
  gap: 6px;
  z-index: 100;
}

.main { margin-left: var(--sw); flex: 1; min-height: 100vh; }

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 2px 8px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 2px;
}

.logo-hex { font-size: 20px; color: var(--indigo); }

.logo-name {
  font-size: 14.5px;
  font-weight: 600;
  color: #F1F5F9;
  letter-spacing: -0.01em;
}

.new-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--indigo);
  color: white;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.14s;
}
.new-btn:hover { background: var(--indigo-d); }

.history-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; margin-top: 6px; }

.nav-label {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #475569;
  padding: 0 8px 6px;
}

.history-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 7px 9px;
  border-radius: 7px;
  transition: background 0.1s;
  cursor: pointer;
}
.history-item:hover, .history-item.active { background: rgba(255,255,255,0.07); }

.h-icon {
  font-size: 11px;
  width: 14px;
  text-align: center;
  margin-top: 3px;
  flex-shrink: 0;
}
.running .h-icon  { color: var(--blue); animation: pulse 1.4s ease infinite; }
.review .h-icon   { color: var(--amber); }
.done .h-icon     { color: var(--green); }
.fail .h-icon     { color: var(--red); }

.h-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; }

.h-task {
  font-size: 12.5px;
  color: #CBD5E1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 178px;
}

.h-date { font-size: 10.5px; color: #475569; }

.no-history { font-size: 12px; color: #475569; padding: 6px 8px; font-style: italic; }

@media (max-width: 768px) {
  .sidebar { display: none; }
  .main { margin-left: 0; }
}
</style>
