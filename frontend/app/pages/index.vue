<script setup lang="ts">
const api = useResearchApi()
const router = useRouter()
const emit = defineEmits(['history-updated'])

const task = ref('')
const hitl = ref(false)
const isLoading = ref(false)
const error = ref('')

const examples = [
  'Latest AI agent frameworks in 2025',
  'Climate tech investment trends',
  'Gene therapy clinical trials progress',
  'Quantum computing real-world applications',
]

const submit = async () => {
  if (!task.value.trim() || isLoading.value) return
  isLoading.value = true
  error.value = ''
  try {
    const { thread_id } = await api.runResearch(task.value.trim(), hitl.value)
    emit('history-updated')
    router.push(`/task/${thread_id}`)
  } catch (e: any) {
    error.value = e?.data?.detail || e?.message || 'Could not connect to the backend (is it running on port 8000?)'
    isLoading.value = false
  }
}
</script>

<template>
  <div class="home">
    <div class="hero">
      <div class="badge">Powered by Claude + Qdrant</div>
      <h1>What would you like to research?</h1>
      <p>AI-powered research that searches the web, validates sources, and builds knowledge over time.</p>
    </div>

    <div class="form-card">
      <form @submit.prevent="submit">
        <textarea
          v-model="task"
          class="topic-input"
          placeholder="Enter a research topic or question…"
          rows="3"
          @keydown.meta.enter="submit"
          @keydown.ctrl.enter="submit"
        />

        <div class="form-footer">
          <label class="hitl-label">
            <input type="checkbox" v-model="hitl" />
            <div>
              <span class="hitl-title">Human review</span>
              <span class="hitl-desc">Pause for your approval before saving results</span>
            </div>
          </label>

          <button type="submit" class="submit-btn" :disabled="!task.trim() || isLoading">
            <span v-if="isLoading" class="spinner-sm" />
            <template v-else>Start Research <span class="arrow">→</span></template>
          </button>
        </div>

        <div v-if="error" class="error-box">{{ error }}</div>
      </form>
    </div>

    <div class="examples-area">
      <span class="ex-label">Try an example</span>
      <div class="ex-chips">
        <button
          v-for="ex in examples"
          :key="ex"
          class="chip"
          @click="task = ex"
        >{{ ex }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 48px 24px;
  gap: 28px;
  animation: fade-in 0.3s ease;
}

.hero {
  text-align: center;
  max-width: 540px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.badge {
  display: inline-flex;
  padding: 4px 12px;
  background: var(--indigo-l);
  color: var(--indigo-d);
  border-radius: 99px;
  font-size: 11.5px;
  font-weight: 500;
  border: 1px solid rgba(99,102,241,0.2);
}

.hero h1 {
  font-size: clamp(22px, 4vw, 34px);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.2;
  color: var(--text);
}

.hero p {
  font-size: 14.5px;
  color: var(--muted);
  max-width: 420px;
}

/* Form */
.form-card {
  width: 100%;
  max-width: 620px;
  background: var(--card);
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 0 1px var(--border);
}

.topic-input {
  width: 100%;
  border: none;
  outline: none;
  font-size: 15.5px;
  color: var(--text);
  resize: none;
  font-family: inherit;
  line-height: 1.55;
  padding: 2px 0 12px;
  border-bottom: 1px solid var(--border);
  background: transparent;
}
.topic-input::placeholder { color: var(--faint); }

.form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  gap: 12px;
  flex-wrap: wrap;
}

.hitl-label {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  cursor: pointer;
  user-select: none;
}
.hitl-label input[type="checkbox"] {
  margin-top: 3px;
  width: 15px;
  height: 15px;
  accent-color: var(--indigo);
  cursor: pointer;
  flex-shrink: 0;
}
.hitl-title { font-size: 13.5px; font-weight: 500; display: block; }
.hitl-desc  { font-size: 11.5px; color: var(--muted); display: block; }

.submit-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 18px;
  background: var(--indigo);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.14s, transform 0.14s, box-shadow 0.14s;
  white-space: nowrap;
  flex-shrink: 0;
  font-family: inherit;
}
.submit-btn:hover:not(:disabled) {
  background: var(--indigo-d);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(99,102,241,0.35);
}
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.arrow { transition: transform 0.14s; }
.submit-btn:hover:not(:disabled) .arrow { transform: translateX(2px); }

.spinner-sm {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
  display: inline-block;
}

.error-box {
  margin-top: 10px;
  padding: 9px 12px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  color: #DC2626;
  border-radius: 7px;
  font-size: 13px;
}

/* Examples */
.examples-area {
  width: 100%;
  max-width: 620px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.ex-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.ex-chips { display: flex; flex-wrap: wrap; gap: 7px; }

.chip {
  padding: 6px 13px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 99px;
  font-size: 12.5px;
  color: var(--text);
  cursor: pointer;
  transition: all 0.12s;
  font-family: inherit;
}
.chip:hover {
  border-color: var(--indigo);
  color: var(--indigo);
  background: var(--indigo-l);
}
</style>
