import type { TaskStatus } from '~/types'

export const useResearchApi = () => {
  const { public: { apiBase } } = useRuntimeConfig()

  return {
    runResearch: (task: string, hitl: boolean) =>
      $fetch<{ thread_id: string; status: string }>(`${apiBase}/run`, {
        method: 'POST',
        body: { task, hitl },
      }),

    getStatus: (threadId: string) =>
      $fetch<TaskStatus>(`${apiBase}/status/${threadId}`),

    submitReview: (threadId: string, action: 'approve' | 'reject', feedback?: string) =>
      $fetch<{ thread_id: string; status: string }>(`${apiBase}/review/${threadId}`, {
        method: 'POST',
        body: { action, feedback },
      }),

    getHistory: () =>
      $fetch<TaskStatus[]>(`${apiBase}/history`),
  }
}
