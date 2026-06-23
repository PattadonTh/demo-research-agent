<script setup lang="ts">
import type { TaskStatus } from '~/types'

const route = useRoute()
const api = useResearchApi()
const emit = defineEmits(['history-updated'])

const status = ref<TaskStatus | null>(null)
const loading = ref(true)
const fetchError = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const reviewMode = ref(false)
const reviewAction = ref<'approve' | 'reject' | null>(null)
const feedback = ref('')
const submitting = ref(false)
const reviewError = ref('')

const threadId = computed(() => route.params.id as string)

const stopPolling = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

const fetchStatus = async () => {
  try {
    status.value = await api.getStatus(threadId.value)
    if (status.value.status !== 'running') stopPolling()
  } catch (e: any) {
    fetchError.value = e?.data?.detail || 'Failed to fetch status'
    stopPolling()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchStatus()
  if (status.value?.status === 'running') {
    pollTimer = setInterval(fetchStatus, 2500)
  }
})
onUnmounted(stopPolling)

const startReview = (action: 'approve' | 'reject') => {
  reviewAction.value = action
  reviewMode.value = action === 'reject'
  if (action === 'approve') submitReview()
}

const cancelReview = () => {
  reviewMode.value = false
  reviewAction.value = null
  feedback.value = ''
  reviewError.value = ''
}

const submitReview = async () => {
  if (!reviewAction.value) return
  if (reviewAction.value === 'reject' && !feedback.value.trim()) return

  submitting.value = true
  reviewError.value = ''
  try {
    await api.submitReview(threadId.value, reviewAction.value, feedback.value.trim() || undefined)
    reviewMode.value = false
    reviewAction.value = null
    feedback.value = ''
    loading.value = true
    status.value = { ...status.value!, status: 'running' }
    pollTimer = setInterval(fetchStatus, 2500)
    emit('history-updated')
  } catch (e: any) {
    reviewError.value = e?.data?.detail || 'Failed to submit review'
  } finally {
    submitting.value = false
  }
}

const formattedDate = computed(() =>
  status.value ? new Date(status.value.created_at).toLocaleString() : ''
)
</script>

<template>
  <!-- Initial load -->
  <div v-if="loading && !status" class="page-center">
    <div class="big-spinner" />
    <span class="load-text">Loading task…</span>
  </div>

  <!-- Hard error (no status object) -->
  <div v-else-if="fetchError && !status" class="page-center">
    <div class="err-card">
      <span class="err-icon">✕</span>
      <h2>Something went wrong</h2>
      <p>{{ fetchError }}</p>
      <NuxtLink to="/" class="btn-back-lg">← Back to home</NuxtLink>
    </div>
  </div>

  <!-- Task view -->
  <div v-else-if="status" class="task-page">
    <!-- Top bar -->
    <div class="topbar">
      <NuxtLink to="/" class="back-link">← Back</NuxtLink>
      <div class="topbar-center">
        <span class="topbar-task">{{ status.task }}</span>
        <span class="status-pill" :class="`pill-${status.status}`">
          {{ status.status.replace('_', ' ') }}
        </span>
      </div>
      <span class="topbar-date">{{ formattedDate }}</span>
    </div>

    <div class="task-body">
      <!-- RUNNING -->
      <div v-if="status.status === 'running'" class="state-running">
        <div class="running-card">
          <div class="running-ring">
            <div class="ring-spinner" />
          </div>
          <div class="running-text">
            <h2>Researching…</h2>
            <p>Searching the web, validating sources, and building your report</p>
          </div>
        </div>
        <ul class="steps">
          <li>Querying knowledge memory for past research</li>
          <li>Searching the web with targeted queries</li>
          <li>Validating source URLs for reachability</li>
          <li>Structuring findings into a structured report</li>
        </ul>
      </div>

      <!-- WAITING REVIEW -->
      <div v-else-if="status.status === 'waiting_review'" class="state-review">
        <div class="review-banner">
          <div class="review-icon">👤</div>
          <div class="review-text">
            <h2>Your review is needed</h2>
            <p>The agent has completed its research. Review the report below, then approve or request changes.</p>
          </div>
          <div v-if="!reviewMode" class="review-btns">
            <button class="btn-reject" @click="startReview('reject')">Request Changes</button>
            <button class="btn-approve" :disabled="submitting" @click="startReview('approve')">
              <span v-if="submitting" class="spinner-sm" />
              <span v-else>✓ Approve</span>
            </button>
          </div>
        </div>

        <!-- Rejection form -->
        <div v-if="reviewMode" class="rejection-form">
          <label class="rej-label">What should be improved?</label>
          <textarea
            v-model="feedback"
            class="rej-textarea"
            placeholder="Describe what needs to be changed or added…"
            rows="3"
          />
          <div v-if="reviewError" class="error-box">{{ reviewError }}</div>
          <div class="rej-footer">
            <button class="btn-cancel" @click="cancelReview">Cancel</button>
            <button
              class="btn-submit-rej"
              :disabled="!feedback.trim() || submitting"
              @click="submitReview"
            >
              <span v-if="submitting" class="spinner-sm" />
              <span v-else>Submit Feedback</span>
            </button>
          </div>
        </div>

        <div v-if="status.result" class="preview-label">Research Preview</div>
        <ReportView v-if="status.result" :report="status.result" />
      </div>

      <!-- COMPLETED -->
      <div v-else-if="status.status === 'completed' && status.result" class="state-done">
        <div class="done-banner">
          <span class="done-icon">✓</span>
          <span>Research complete — saved to memory</span>
        </div>
        <ReportView :report="status.result" />
      </div>

      <!-- FAILED -->
      <div v-else-if="status.status === 'failed'" class="state-failed">
        <div class="failed-card">
          <span class="failed-icon">✕</span>
          <h2>Research failed</h2>
          <p>{{ status.error || 'An unexpected error occurred during research.' }}</p>
          <NuxtLink to="/" class="btn-retry">Try Again →</NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Page-level centering (loading / error) */
.page-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: 14px;
  color: var(--muted);
}

.big-spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--indigo);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.load-text { font-size: 14px; }

.err-card {
  text-align: center;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 36px 40px;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.err-icon {
  width: 44px; height: 44px;
  background: #FEE2E2;
  color: var(--red);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
}
.err-card h2 { font-size: 18px; font-weight: 600; }
.err-card p  { font-size: 13.5px; color: var(--muted); }

.btn-back-lg {
  margin-top: 6px;
  padding: 8px 16px;
  background: var(--indigo-l);
  color: var(--indigo-d);
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
}

/* Layout */
.task-page { display: flex; flex-direction: column; min-height: 100vh; }

/* Topbar */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  background: var(--card);
  border-bottom: 1px solid var(--border);
  gap: 12px;
  flex-wrap: wrap;
  position: sticky;
  top: 0;
  z-index: 50;
}

.back-link {
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
  transition: color 0.12s;
  white-space: nowrap;
}
.back-link:hover { color: var(--text); }

.topbar-center {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  justify-content: center;
  min-width: 0;
}

.topbar-task {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 360px;
}

.status-pill {
  padding: 3px 10px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.pill-running        { background: #DBEAFE; color: #1D4ED8; }
.pill-waiting_review { background: #FEF3C7; color: #92400E; }
.pill-completed      { background: #DCFCE7; color: #15803D; }
.pill-failed         { background: #FEE2E2; color: #B91C1C; }

.topbar-date { font-size: 12px; color: var(--faint); white-space: nowrap; }

/* Task body */
.task-body { flex: 1; padding: 28px; max-width: 860px; margin: 0 auto; width: 100%; }

/* Running state */
.state-running { display: flex; flex-direction: column; gap: 20px; animation: fade-in 0.3s ease; }

.running-card {
  display: flex;
  align-items: center;
  gap: 24px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 28px 32px;
}

.running-ring {
  width: 52px; height: 52px;
  background: var(--indigo-l);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ring-spinner {
  width: 28px; height: 28px;
  border: 3px solid rgba(99,102,241,0.25);
  border-top-color: var(--indigo);
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

.running-text h2 { font-size: 18px; font-weight: 600; margin-bottom: 5px; }
.running-text p  { font-size: 14px; color: var(--muted); }

.steps {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 0 4px;
}
.steps li {
  font-size: 13px;
  color: var(--muted);
  padding-left: 22px;
  position: relative;
}
.steps li::before {
  content: '·';
  position: absolute;
  left: 8px;
  color: var(--indigo);
  font-size: 20px;
  line-height: 1;
  top: -1px;
}

/* Review state */
.state-review { display: flex; flex-direction: column; gap: 20px; animation: fade-in 0.3s ease; }

.review-banner {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  border-radius: 12px;
  padding: 20px 24px;
  flex-wrap: wrap;
}

.review-icon {
  width: 44px; height: 44px;
  background: #FEF3C7;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.review-text { flex: 1; min-width: 200px; }
.review-text h2 { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.review-text p  { font-size: 13.5px; color: #78350F; }

.review-btns { display: flex; align-items: center; gap: 8px; flex-shrink: 0; align-self: center; }

.btn-reject {
  padding: 8px 14px;
  background: white;
  border: 1px solid #FDE68A;
  border-radius: 7px;
  font-size: 13px;
  color: #92400E;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.12s;
}
.btn-reject:hover { background: #FEF9C3; }

.btn-approve {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--green);
  color: white;
  border: none;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: filter 0.12s;
}
.btn-approve:hover:not(:disabled) { filter: brightness(1.08); }
.btn-approve:disabled { opacity: 0.6; cursor: not-allowed; }

/* Rejection form */
.rejection-form {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: fade-in 0.2s ease;
}

.rej-label { font-size: 14px; font-weight: 500; }

.rej-textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  color: var(--text);
  resize: vertical;
  outline: none;
  transition: border-color 0.14s;
}
.rej-textarea:focus { border-color: var(--indigo); }

.rej-footer { display: flex; justify-content: flex-end; gap: 8px; }

.btn-cancel {
  padding: 8px 14px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 7px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
}
.btn-cancel:hover { background: var(--bg); }

.btn-submit-rej {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--indigo);
  color: white;
  border: none;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.12s;
}
.btn-submit-rej:hover:not(:disabled) { background: var(--indigo-d); }
.btn-submit-rej:disabled { opacity: 0.5; cursor: not-allowed; }

.preview-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
}

/* Done state */
.state-done { display: flex; flex-direction: column; gap: 20px; animation: fade-in 0.3s ease; }

.done-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #F0FDF4;
  border: 1px solid #BBF7D0;
  border-radius: 9px;
  padding: 11px 16px;
  font-size: 13.5px;
  color: #15803D;
  font-weight: 500;
}

.done-icon {
  width: 22px; height: 22px;
  background: #22C55E;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

/* Failed state */
.state-failed {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
}

.failed-card {
  text-align: center;
  background: var(--card);
  border: 1px solid #FECACA;
  border-radius: 14px;
  padding: 36px 40px;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.failed-icon {
  width: 48px; height: 48px;
  background: #FEE2E2;
  color: var(--red);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}

.failed-card h2 { font-size: 18px; font-weight: 600; }
.failed-card p  { font-size: 13.5px; color: var(--muted); }

.btn-retry {
  margin-top: 6px;
  padding: 9px 18px;
  background: var(--indigo);
  color: white;
  border-radius: 8px;
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.12s;
}
.btn-retry:hover { background: var(--indigo-d); }

/* Shared */
.spinner-sm {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
  display: inline-block;
}

.error-box {
  padding: 9px 12px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  color: #DC2626;
  border-radius: 7px;
  font-size: 13px;
}
</style>
