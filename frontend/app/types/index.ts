export interface Source {
  title: string
  url: string
  relevance: 'high' | 'medium' | 'low'
}

export interface AgentOutput {
  title: string
  summary: string
  key_findings: string[]
  sections: Record<string, string>
  sources: Source[]
  limitations: string
}

export interface TaskStatus {
  thread_id: string
  task: string
  status: 'running' | 'waiting_review' | 'completed' | 'failed'
  result: AgentOutput | null
  error: string | null
  created_at: string
}
