import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Logo } from '../components/Logo'
import { CodePane } from '../exercise/CodePane'
import type { CodePaneHandle, LineMark } from '../exercise/CodePane'
import { Timer } from '../exercise/Header'
import { Sidebar } from '../exercise/Sidebar'
import { loadExercise, primaryFile } from '../lib/files'
import type { CodeFile } from '../lib/files'
import { functionAt } from '../lib/outline'
import {
  TASK_LABEL, buildTaskSubmission, canSubmitTask, clearTaskAnswer, emptyTaskAnswer, loadTaskAnswer, saveTaskAnswer,
  taskTitle, ticketParts,
} from '../lib/tasks'
import type { TaskAnswer, TaskSubmission } from '../lib/tasks'
import { CONFIDENCES, LABEL, formatRanges } from '../lib/types'
import type { PublicExercise, PublicTask, Range } from '../lib/types'

const CANDIDATE_ID = 'local' // no accounts yet
const MINUTES: Record<PublicTask['type'], number> = { incident: 15, review_pr: 10, trace: 5 }

export default function TaskPage({ id, taskId }: { id: string; taskId: string }) {
  const [loaded, setLoaded] = useState<{ ex: PublicExercise; files: CodeFile[] } | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    loadExercise(id).then(
      (l) => { if (!cancelled) setLoaded(l) },
      (e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)) },
    )
    return () => { cancelled = true }
  }, [id])

  const task = loaded?.ex.tasks?.find((t) => t.id === taskId)
  if (error) return <Message title="Could not open this task" body={error} />
  if (!loaded) return <Message title="Loading…" />
  if (!task) return <Message title="Could not open this task" body={`${id} has no task ${taskId}.`} />
  return <TaskWorkspace key={`${id}:${loaded.ex.version}:${taskId}`} ex={loaded.ex} files={loaded.files} task={task} />
}

function TaskWorkspace({ ex, files, task }: { ex: PublicExercise; files: CodeFile[]; task: PublicTask }) {
  // A PR review opens the file the diff changes; everything else opens the main file.
  const [path, setPath] = useState(() => {
    const changed = /^\+\+\+ b\/(.+)$/m.exec(task.diff ?? '')?.[1]
    return files.some((f) => f.path === changed) ? changed! : primaryFile(ex, files).path
  })
  const file = files.find((f) => f.path === path) ?? files[0]
  const [answer, setAnswer] = useState<TaskAnswer>(() => loadTaskAnswer(ex.id, ex.version, task.id) ?? emptyTaskAnswer())
  useEffect(() => saveTaskAnswer(ex.id, ex.version, task.id, answer), [answer, ex, task])
  const [topLine, setTopLine] = useState(1)
  const [query, setQuery] = useState('')
  const [hitIdx, setHitIdx] = useState(0)
  const [submitted, setSubmitted] = useState<TaskSubmission | null>(null)
  const code = useRef<CodePaneHandle>(null)
  const search = useRef<HTMLInputElement>(null)
  const pendingScroll = useRef<number | null>(null)

  useEffect(() => {
    if (pendingScroll.current != null) {
      code.current?.scrollToLine(pendingScroll.current)
      pendingScroll.current = null
    }
  })
  const jump = useCallback((line: number, toFile?: string) => {
    if (toFile && toFile !== path) { setPath(toFile); pendingScroll.current = line } else code.current?.scrollToLine(line)
  }, [path])
  const openFile = (p: string) => { setPath(p); setQuery(''); setTopLine(1); pendingScroll.current = 1 }

  const hits = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? file.lines.flatMap((l, i) => (l.toLowerCase().includes(q) ? [i + 1] : [])) : []
  }, [query, file])
  const activeHit = hits.length ? hits[Math.min(hitIdx, hits.length - 1)] : null
  useEffect(() => { if (activeHit != null) jump(activeHit) }, [query])

  const onSelect = useCallback((start: number, end: number) => {
    setAnswer((a) => ({ ...a, ranges: [...a.ranges, { file: path, start_line: start, end_line: end }] }))
  }, [path])
  const removeRange = (i: number) => setAnswer((a) => ({ ...a, ranges: a.ranges.filter((_, j) => j !== i) }))

  const marks = useMemo(() => {
    const m = new Map<number, LineMark>()
    for (const r of answer.ranges) if (r.file === path) for (let n = r.start_line; n <= r.end_line; n++) m.set(n, 'saved')
    return m
  }, [answer.ranges, path])
  const fileList = files.map((f) => ({ path: f.path, comments: answer.ranges.filter((r) => r.file === f.path).length }))

  const submit = () => {
    setSubmitted(buildTaskSubmission(ex, task, answer, CANDIDATE_ID))
    clearTaskAnswer(ex.id, ex.version, task.id)
  }
  if (submitted) return <TaskSubmitted sub={submitted} ex={ex} task={task} />

  const ready = canSubmitTask(task, answer)
  return (
    <div className="flex h-screen flex-col bg-canvas">
      <header className="flex h-14 flex-none items-center gap-5 border-b border-line bg-white px-5">
        <Logo />
        <div className="h-6 w-px bg-line" />
        <div className="flex min-w-0 flex-col leading-tight">
          <span className="truncate text-sm font-semibold">{TASK_LABEL[task.type]} · {taskTitle(task)}</span>
          <span className="truncate text-xs text-muted">{ex.title} · {files.length} file{files.length === 1 ? '' : 's'}</span>
        </div>
        <div className="flex-1" />
        <a href="#/exercises" className="text-xs text-muted hover:text-ink">All exercises</a>
        <Timer startedAt={answer.startedAt} minutes={MINUTES[task.type]} />
        <button type="button" disabled={!ready} onClick={submit}
          title={ready ? undefined : 'Answer every required part first'}
          className="h-9 rounded-lg bg-accent px-4 font-semibold text-white hover:bg-[#1a44bd] disabled:opacity-40">
          Submit
        </button>
      </header>
      <div className="flex min-h-0 flex-1">
        <Sidebar ref={search} files={fileList} activeFile={path} onOpenFile={openFile} sections={file.sections}
          currentFn={functionAt(file.sections, topLine)?.name} savedCount={new Map()} draftFn={undefined}
          query={query} onQuery={(q) => { setQuery(q); setHitIdx(0) }}
          onNextHit={(back) => {
            if (!hits.length) return
            const i = (Math.min(hitIdx, hits.length - 1) + (back ? hits.length - 1 : 1)) % hits.length
            setHitIdx(i)
            jump(hits[i])
          }}
          onJump={jump} hitInfo={hits.length ? `${Math.min(hitIdx, hits.length - 1) + 1} of ${hits.length} · Enter for next` : 'No matches'} />
        <CodePane ref={code} path={path} tokens={file.tokens} marks={marks} inserts={new Map()} focusLines={null}
          searchHits={new Set(hits)} activeHit={activeHit} breadcrumb={functionAt(file.sections, topLine)?.name}
          onSelect={onSelect} onTopLineChange={setTopLine} onShowAll={() => {}} focus={false} canFocus={false}
          onToggleFocus={() => {}} />
        <aside className="flex w-[420px] flex-none flex-col overflow-y-auto border-l border-line bg-white">
          <div className="flex flex-col gap-5 p-5">
            <TaskBrief task={task} />
            <AnswerForm task={task} answer={answer} setAnswer={setAnswer} onJump={jump} onRemove={removeRange} />
          </div>
        </aside>
      </div>
    </div>
  )
}

function TaskBrief({ task }: { task: PublicTask }) {
  if (task.type === 'incident') {
    const { from, quote, ask } = ticketParts(task)
    return (
      <div>
        <div className="text-[11px] font-semibold tracking-[0.06em] text-muted">INCIDENT</div>
        <div className="mt-2 overflow-hidden rounded-[10px] border border-line">
          <div className="flex items-center justify-between border-b border-line bg-panel px-3.5 py-2 text-xs">
            <span className="font-semibold">{from || 'Ticket'}</span>
            <span className="rounded bg-bug-soft px-1.5 py-px font-medium">Open</span>
          </div>
          {quote && <p className="whitespace-pre-wrap px-3.5 py-3 text-[13.5px] leading-[1.55]">{quote}</p>}
        </div>
        <p className="mt-3 text-[13px] leading-[1.5] text-muted">{ask}</p>
      </div>
    )
  }
  return (
    <div>
      <div className="text-[11px] font-semibold tracking-[0.06em] text-muted">{TASK_LABEL[task.type].toUpperCase()}</div>
      <p className="mt-2 text-[13.5px] leading-[1.55]">{task.text}</p>
      {task.diff && <DiffView diff={task.diff} />}
    </div>
  )
}

function DiffView({ diff }: { diff: string }) {
  return (
    <pre className="mt-3 overflow-x-auto rounded-[10px] bg-code-bg py-2.5 font-mono text-[12px] leading-5 text-code-text">
      {diff.replace(/\n$/, '').split('\n').map((l, i) => {
        const cls = l.startsWith('+++') || l.startsWith('---') ? 'text-code-dim'
          : l.startsWith('+') ? 'bg-[rgba(46,160,67,0.22)]'
            : l.startsWith('-') ? 'bg-[rgba(248,81,73,0.22)]'
              : l.startsWith('@@') ? 'text-code-pre' : ''
        return <div key={i} className={`px-3 ${cls}`}>{l || ' '}</div>
      })}
    </pre>
  )
}

function AnswerForm({ task, answer, setAnswer, onJump, onRemove }: {
  task: PublicTask
  answer: TaskAnswer
  setAnswer: (f: (a: TaskAnswer) => TaskAnswer) => void
  onJump: (line: number, file?: string) => void
  onRemove: (i: number) => void
}) {
  const set = (patch: Partial<TaskAnswer>) => setAnswer((a) => ({ ...a, ...patch }))
  const field = 'w-full resize-y rounded-lg border border-line-strong px-2.5 py-2 text-[13px] leading-[1.45] outline-none focus:border-accent'
  const label = 'mb-1.5 block text-[12.5px] font-semibold'
  return (
    <div className="flex flex-col gap-4 border-t border-line pt-5">
      {task.type === 'review_pr' && (
        <fieldset>
          <legend className={label}>Your review</legend>
          <div className="flex gap-2">
            {(['approve', 'request_changes'] as const).map((v) => (
              <button key={v} type="button" onClick={() => set({ verdict: v })}
                className={`h-9 flex-1 rounded-lg border font-medium ${answer.verdict === v ? 'border-accent bg-accent-soft text-accent' : 'border-line-strong hover:border-ink'}`}>
                {v === 'approve' ? 'Approve' : 'Request changes'}
              </button>
            ))}
          </div>
        </fieldset>
      )}
      {task.type === 'trace' && (
        <fieldset>
          <legend className={label}>Your answer</legend>
          <div className="flex flex-col gap-1.5">
            {task.options?.map((o) => (
              <label key={o.id} className={`flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 text-[13px] ${answer.option === o.id ? 'border-accent bg-accent-soft' : 'border-line-strong hover:border-ink'}`}>
                <input type="radio" name="option" className="mt-0.5" checked={answer.option === o.id} onChange={() => set({ option: o.id })} />
                <span><b className="font-mono font-semibold">{o.id})</b> {o.text}</span>
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div>
        <span className={label}>
          {task.type === 'incident' ? 'Where is the cause?' : 'Point at the code (optional)'}
        </span>
        <p className="mb-2 text-xs leading-[1.45] text-muted">
          Drag across line numbers in any file to add a location. {task.type === 'incident' && 'Add more than one if the cause spans files.'}
        </p>
        {answer.ranges.length === 0
          ? <div className="rounded-lg border border-dashed border-line-strong px-3 py-2.5 text-xs text-muted">No lines selected yet.</div>
          : (
            <div className="flex flex-col gap-1">
              {answer.ranges.map((r: Range, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-accent-soft px-2.5 py-1.5 text-xs">
                  <button type="button" onClick={() => onJump(r.start_line, r.file)} className="font-mono hover:underline">
                    {r.file} · {formatRanges([r])}
                  </button>
                  <button type="button" aria-label="Remove location" onClick={() => onRemove(i)} className="px-1 text-muted hover:text-ink">×</button>
                </div>
              ))}
            </div>
          )}
      </div>

      <label>
        <span className={label}>
          {task.type === 'incident' ? 'What is going wrong, and why does it cause what the customer sees?'
            : task.type === 'review_pr' ? 'Why? What did you check?' : 'Explain how you got there'}
        </span>
        <textarea className={`${field} h-[130px]`} value={answer.explanation} onChange={(e) => set({ explanation: e.target.value })} />
      </label>
      {task.type === 'incident' && (
        <label>
          <span className={label}>How would you fix it? <span className="font-normal text-muted">(optional)</span></span>
          <textarea className={`${field} h-[70px]`} value={answer.fix} onChange={(e) => set({ fix: e.target.value })} />
        </label>
      )}
      <label>
        <span className={label}>How sure are you?</span>
        <select value={answer.confidence} onChange={(e) => set({ confidence: e.target.value as TaskAnswer['confidence'] })}
          className="h-9 w-full rounded-lg border border-line-strong bg-white px-2 text-[13px]">
          {CONFIDENCES.map((c) => <option key={c} value={c}>{LABEL[c]}</option>)}
        </select>
      </label>
    </div>
  )
}

function TaskSubmitted({ sub, ex, task }: { sub: TaskSubmission; ex: PublicExercise; task: PublicTask }) {
  const json = JSON.stringify(sub, null, 2)
  const tasks = ex.tasks ?? []
  const next = tasks[tasks.findIndex((t) => t.id === task.id) + 1]
  return (
    <div className="min-h-screen bg-canvas">
      <header className="flex h-14 items-center gap-5 border-b border-line bg-white px-5"><Logo /></header>
      <div className="mx-auto max-w-[760px] px-4 py-10">
        <h1 className="text-xl font-semibold">Submitted: {TASK_LABEL[task.type]} · {taskTitle(task)}</h1>
        <p className="mt-2 text-muted">{sub.time_spent_minutes} minutes · {sub.locations.length} location{sub.locations.length === 1 ? '' : 's'} · {LABEL[sub.confidence]}</p>
        <div className="mt-5 rounded-[10px] border border-line bg-white p-4 leading-[1.5]">
          <b className="font-semibold">Grading isn't connected to this page yet.</b> To grade locally, save the submission as a file and run{' '}
          <code className="rounded bg-chip px-1.5 py-px font-mono text-[12.5px]">cd backend && python -m grader ../examples/{ex.id} task.json</code>
        </div>
        <div className="mt-4 flex gap-2">
          {next && <a href={`#/exercise/${ex.id}/task/${next.id}`} className="flex h-9 items-center rounded-lg bg-accent px-4 font-semibold text-white">Next: {TASK_LABEL[next.type]} →</a>}
          <a href="#/exercises" className="flex h-9 items-center rounded-lg border border-line-strong bg-white px-3.5 font-medium hover:border-ink">Back to exercises</a>
        </div>
        <pre className="mt-4 max-h-[60vh] overflow-auto rounded-[10px] bg-code-bg p-4 font-mono text-xs leading-5 text-code-text">{json}</pre>
      </div>
    </div>
  )
}

function Message({ title, body }: { title: string; body?: string }) {
  return (
    <div className="min-h-screen bg-canvas">
      <header className="flex h-14 items-center border-b border-line bg-white px-5"><Logo /></header>
      <div className="mx-auto max-w-[560px] px-4 py-16">
        <h1 className="text-lg font-semibold">{title}</h1>
        {body && <p className="mt-2 text-muted">{body}</p>}
        {body && <a href="#/exercises" className="mt-4 inline-block font-medium text-accent hover:underline">Back to exercises</a>}
      </div>
    </div>
  )
}
