// Shapes of public.json (schemas/public.schema.json) and of the candidate's in-progress work.

const LANGUAGE_LABELS: Record<string, string> = {
  c: 'C', cpp: 'C++', python: 'Python', go: 'Go', rust: 'Rust', java: 'Java',
  javascript: 'JavaScript', typescript: 'TypeScript',
}

export function languageLabel(language: string): string {
  return LANGUAGE_LABELS[language] ?? language
}

export type TaskType = 'incident' | 'review_pr' | 'trace'

// An incident ticket, a PR to review, or a trace question (multiple choice).
export interface PublicTask {
  id: string
  type: TaskType
  text: string
  diff?: string
  options?: { id: string; text: string }[]
}

export interface ExerciseSummary {
  id: string
  version: number
  title: string
  language: string
  difficulty: string
  track?: string
  area?: string
  rung?: number
  topics: string[]
  estimated_minutes: number
  line_count: number
  tasks?: PublicTask[]
}

// What index.json adds per exercise (tools/sync_public.py).
export interface ExerciseListItem extends ExerciseSummary {
  track_name: string
  area_name: string
  in_mvp: boolean
}

export interface PublicExercise extends Omit<ExerciseSummary, 'line_count'> {
  files: { path: string; line_count: number }[]
  license: { spdx: string; attribution: string }
  questions: { id: string; text: string }[]
  design_prompts: { id: string; text: string }[]
}

export type CommentType = 'bug' | 'question' | 'design' | 'improvement'
export type Severity = 'low' | 'medium' | 'high' | 'critical'
export type Confidence = 'guess' | 'fairly_sure' | 'certain'

export interface Range {
  file: string
  start_line: number
  end_line: number
}

export interface CodeComment {
  id: string
  type: CommentType
  ranges: Range[]
  text: string
  severity?: Severity
  confidence?: Confidence
  fix?: string
  function?: string
}

export interface Improvement {
  id: string
  title: string
  detail: string
}

export interface Answers {
  startedAt: number
  comprehension: Record<string, string>
  design: Record<string, string>
  comments: CodeComment[]
  improvements: Improvement[]
}

export const SEVERITIES: Severity[] = ['low', 'medium', 'high', 'critical']
export const CONFIDENCES: Confidence[] = ['guess', 'fairly_sure', 'certain']
export const COMMENT_TYPES: CommentType[] = ['bug', 'question', 'design', 'improvement']

export const LABEL: Record<CommentType | Severity | Confidence, string> = {
  bug: 'Bug',
  question: 'Question',
  design: 'Design concern',
  improvement: 'Improvement',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
  guess: 'Guess',
  fairly_sure: 'Fairly sure',
  certain: 'Certain',
}

export function formatRanges(ranges: Range[]): string {
  const parts = ranges.map((r) => (r.start_line === r.end_line ? `${r.start_line}` : `${r.start_line}–${r.end_line}`))
  return `${ranges.length === 1 && ranges[0].start_line === ranges[0].end_line ? 'line' : 'lines'} ${parts.join(', ')}`
}
