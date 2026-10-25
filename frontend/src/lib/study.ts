// Study mode: one participant code, one sitting. The form (set of tasks) comes
// from a hash of the code that backend/study computes the same way, so the
// server can check it. Progress autosaves so a refresh does not lose work.
import type { TaskSubmission } from './tasks'

export interface StudyQuestion {
  id: string
  label: string
  type: 'choice' | 'text'
  required: boolean
  options?: string[]
}

export interface Study {
  schema_version: 1
  id: string
  title: string
  estimated_minutes: number
  consent: string[]
  survey: StudyQuestion[]
  honesty: StudyQuestion[]
  end_title?: string   // heading and intro for the closing questions (defaults suit the pilot)
  end_intro?: string
  fixed_first: number
  forms: Record<string, { exercise: string; task: string }[]>
}

export type Stage = 'consent' | 'survey' | 'tasks' | 'honesty' | 'submitting' | 'done'

export interface StudyProgress {
  stage: Stage
  consent_at?: string
  started_at: string
  survey: Record<string, string>
  honesty: Record<string, string>
  index: number
  tasks: TaskSubmission[]
  report?: StudyReport
}

export interface StudyReport {
  participant: string
  percent: number
  level: string
  tasks: { exercise: string; task: string; title: string; score: number; max: number; parts: Record<string, number>; skills: string[] }[]
  comparison: { level: string; peers_at_level: number; peers_total: number; level_median?: number; percentile?: number }
}

export const CODE_PATTERN = /^[A-Za-z0-9_-]{3,40}$/

/** 32-bit FNV-1a, identical to backend/study.fnv1a. */
export function fnv1a(text: string): number {
  let h = 0x811c9dc5
  for (const b of new TextEncoder().encode(text)) {
    h ^= b
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h >>> 0
}

export function formFor(study: Study, code: string): string {
  const names = Object.keys(study.forms).sort()
  return names[fnv1a(code) % names.length]
}

/** The first tasks keep their order (easy warm-up); the rest are shuffled per
 * participant, so fatigue does not always land on the same questions. */
export function orderFor(study: Study, code: string): { exercise: string; task: string }[] {
  const tasks = study.forms[formFor(study, code)]
  const head = tasks.slice(0, study.fixed_first)
  const tail = tasks.slice(study.fixed_first)
  let seed = fnv1a(`${code}:order`) || 1
  const rand = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0
    return seed / 2 ** 32
  }
  for (let i = tail.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    ;[tail[i], tail[j]] = [tail[j], tail[i]]
  }
  return [...head, ...tail]
}

export function missingAnswers(questions: StudyQuestion[], answers: Record<string, string>): string[] {
  return questions.filter((q) => q.required && !answers[q.id]).map((q) => q.id)
}

const key = (study: string, code: string) => `readcode:study:${study}:${code}`

export function newProgress(): StudyProgress {
  return { stage: 'consent', started_at: new Date().toISOString(), survey: {}, honesty: {}, index: 0, tasks: [] }
}

export function loadProgress(study: string, code: string): StudyProgress | null {
  try {
    const raw = localStorage.getItem(key(study, code))
    return raw ? { ...newProgress(), ...JSON.parse(raw) } : null
  } catch {
    return null
  }
}

export function saveProgress(study: string, code: string, p: StudyProgress) {
  try {
    localStorage.setItem(key(study, code), JSON.stringify(p))
  } catch {
    // Storage blocked: the study still works in this tab.
  }
}

export function buildBundle(study: Study, code: string, p: StudyProgress) {
  return {
    schema_version: 1 as const,
    study_id: study.id,
    participant: code,
    form: formFor(study, code),
    order: orderFor(study, code).map((t) => `${t.exercise}:${t.task}`),
    consent_at: p.consent_at,
    started_at: p.started_at,
    finished_at: new Date().toISOString(),
    survey: p.survey,
    honesty: p.honesty,
    tasks: p.tasks,
  }
}
