// Task mode: one incident ticket, PR review or trace question at a time.
// Answers autosave like the full review; submitting produces a task submission
// (schemas/task-submission.schema.json) for the grader.
import type { Confidence, PublicExercise, PublicTask, Range, TaskType } from './types'

export interface TaskAnswer {
  startedAt: number
  ranges: Range[]          // where the candidate says the cause is (incident) or what they point at
  explanation: string
  fix: string
  verdict?: 'approve' | 'request_changes'
  option?: string
  confidence: Confidence
}

export interface TaskSubmission {
  schema_version: 1
  exercise_id: string
  exercise_version: number
  task_id: string
  task_type: TaskType
  candidate_id: string
  submitted_at: string
  time_spent_minutes: number
  locations: Range[]
  explanation: string
  fix?: string
  verdict?: 'approve' | 'request_changes'
  option?: string
  confidence: Confidence
}

export const TASK_LABEL: Record<TaskType, string> = {
  incident: 'Incident',
  review_pr: 'PR review',
  trace: 'Trace',
}

// "Support ticket #5120 (Acme): \"...\" Find the cause..." -> "Support ticket #5120 (Acme)"
export function taskTitle(t: PublicTask): string {
  const head = t.text.split(/:\s/)[0]
  if (t.type === 'incident' && head.length < 60) return head
  const first = t.text.split(/(?<=[.?])\s/)[0]
  return first.length > 90 ? first.slice(0, 89) + '…' : first
}

// The part of an incident ticket in quotes: what the customer actually said.
export function ticketParts(t: PublicTask): { from: string; quote: string | null; ask: string } {
  const m = /^(.*?):\s*"([\s\S]*)"\s*([\s\S]*)$/.exec(t.text)
  return m ? { from: m[1], quote: m[2], ask: m[3] } : { from: '', quote: null, ask: t.text }
}

export function canSubmitTask(t: PublicTask, a: TaskAnswer): boolean {
  if (!a.explanation.trim()) return false
  if (t.type === 'incident') return a.ranges.length > 0
  if (t.type === 'review_pr') return !!a.verdict
  return !!a.option
}

const key = (id: string, version: number, task: string) => `readcode:task:${id}:v${version}:${task}`

export function emptyTaskAnswer(): TaskAnswer {
  return { startedAt: Date.now(), ranges: [], explanation: '', fix: '', confidence: 'fairly_sure' }
}

export function loadTaskAnswer(id: string, version: number, task: string): TaskAnswer | null {
  try {
    const raw = localStorage.getItem(key(id, version, task))
    return raw ? { ...emptyTaskAnswer(), ...JSON.parse(raw) } : null
  } catch {
    return null
  }
}

export function saveTaskAnswer(id: string, version: number, task: string, a: TaskAnswer) {
  try {
    localStorage.setItem(key(id, version, task), JSON.stringify(a))
  } catch {
    // Storage blocked: the page still works, it just won't survive a refresh.
  }
}

export function clearTaskAnswer(id: string, version: number, task: string) {
  try {
    localStorage.removeItem(key(id, version, task))
  } catch {
    /* ignore */
  }
}

export function buildTaskSubmission(ex: PublicExercise, t: PublicTask, a: TaskAnswer, candidateId: string,
  now = new Date()): TaskSubmission {
  return {
    schema_version: 1,
    exercise_id: ex.id,
    exercise_version: ex.version,
    task_id: t.id,
    task_type: t.type,
    candidate_id: candidateId,
    submitted_at: now.toISOString(),
    time_spent_minutes: Math.max(0, Math.round((now.getTime() - a.startedAt) / 6000) / 10),
    locations: [...a.ranges].sort((x, y) => x.file.localeCompare(y.file) || x.start_line - y.start_line),
    explanation: a.explanation.trim(),
    ...(a.fix.trim() ? { fix: a.fix.trim() } : {}),
    ...(t.type === 'review_pr' && a.verdict ? { verdict: a.verdict } : {}),
    ...(t.type === 'trace' && a.option ? { option: a.option } : {}),
    confidence: a.confidence,
  }
}
