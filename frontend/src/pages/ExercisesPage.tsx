import { useEffect, useState } from 'react'
import { Logo } from '../components/Logo'
import { hasProgress } from '../lib/storage'
import { TASK_LABEL, loadTaskAnswer, taskTitle } from '../lib/tasks'
import { languageLabel, type ExerciseListItem, type PublicTask } from '../lib/types'

const TASK_ORDER: PublicTask['type'][] = ['incident', 'review_pr', 'trace']
const TASK_MINUTES: Record<PublicTask['type'], number> = { incident: 15, review_pr: 10, trace: 5 }
const TASK_CHIP: Record<PublicTask['type'], string> = {
  incident: 'bg-[#FDE8E8] text-[#9B1C1C]',
  review_pr: 'bg-accent-soft text-accent',
  trace: 'bg-chip text-muted',
}

export default function ExercisesPage() {
  const [list, setList] = useState<ExerciseListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/exercises/index.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('The exercise list is missing. Run `npm run sync`.'))))
      .then(setList)
      .catch((e) => setError(e.message))
  }, [])

  const main = list?.filter((e) => e.in_mvp) ?? []
  const other = list?.filter((e) => !e.in_mvp) ?? []
  return (
    <div className="min-h-screen bg-canvas">
      <header className="flex h-14 items-center border-b border-line bg-white px-5"><Logo /></header>
      <div className="mx-auto max-w-[880px] px-4 py-10">
        <h1 className="text-xl font-semibold">Exercises</h1>
        <p className="mt-1 text-muted">
          Start with a ticket: a customer reports a symptom, and you find the cause in code you have never seen.
          Then try the full review, where you hunt for every bug yourself.
        </p>
        {error && <p className="mt-6 rounded-lg border border-line bg-white p-4 text-danger">{error}</p>}
        {!list && !error && <p className="mt-6 text-muted">Loading…</p>}
        <div className="mt-6 flex flex-col gap-4">
          {main.map((e) => <ExerciseCard key={e.id} e={e} />)}
        </div>
        {other.length > 0 && (
          <details className="mt-8">
            <summary className="cursor-pointer text-sm font-medium text-muted">Other tracks ({other.length})</summary>
            <div className="mt-3 flex flex-col gap-4">{other.map((e) => <ExerciseCard key={e.id} e={e} />)}</div>
          </details>
        )}
      </div>
    </div>
  )
}

function ExerciseCard({ e }: { e: ExerciseListItem }) {
  const started = hasProgress(e.id, e.version)
  const tasks = [...(e.tasks ?? [])].sort((a, b) => TASK_ORDER.indexOf(a.type) - TASK_ORDER.indexOf(b.type))
  return (
    <div className="rounded-[10px] border border-line bg-white">
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
          <span className="rounded bg-chip px-2 py-0.5 font-medium text-ink">{e.track_name}</span>
          <span>›</span>
          <span>{e.area_name}</span>
        </div>
        <div className="mt-2 text-[15px] font-semibold">{e.title}</div>
        <div className="mt-0.5 text-xs text-muted">
          Exercise {e.id.replace(/^readcode-/, '')} · {languageLabel(e.language)} · {e.line_count} lines
          {!e.has_review && ' · real bug, fixed upstream'}
          {e.rung ? ` · rung ${e.rung} of 5` : ''} · <span className="capitalize">{e.difficulty}</span>
        </div>
      </div>
      {tasks.length > 0 && (
        <div className="border-t border-line">
          {tasks.map((t) => {
            const inProgress = !!loadTaskAnswer(e.id, e.version, t.id)
            return (
              <a key={t.id} href={`#/exercise/${e.id}/task/${t.id}`}
                className="flex items-center gap-3 border-b border-line px-4 py-2.5 last:border-b-0 hover:bg-panel">
                <span className={`w-[78px] flex-none rounded px-2 py-0.5 text-center text-[11px] font-semibold ${TASK_CHIP[t.type]}`}>
                  {TASK_LABEL[t.type]}
                </span>
                <span className="min-w-0 flex-1 truncate text-[13px]">{taskTitle(t)}</span>
                <span className="flex-none text-xs text-muted">{inProgress ? 'In progress' : `~${TASK_MINUTES[t.type]} min`} →</span>
              </a>
            )
          })}
        </div>
      )}
      {e.has_review && <div className="flex items-center justify-between gap-3 border-t border-line bg-panel px-4 py-3">
        <span className="text-xs text-muted">Full review: find every bug, answer the design questions · about {e.estimated_minutes} min</span>
        <a href={`#/exercise/${e.id}`}
          className={`flex h-8 flex-none items-center rounded-lg px-3.5 text-[13px] font-semibold ${tasks.length ? 'border border-line-strong bg-white hover:border-ink' : 'bg-accent text-white'}`}>
          {started ? 'Continue review' : 'Full review'} →
        </a>
      </div>}
    </div>
  )
}
