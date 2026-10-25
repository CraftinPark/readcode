import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Logo } from '../components/Logo'
import { loadExercise } from '../lib/files'
import type { CodeFile } from '../lib/files'
import {
  CODE_PATTERN, buildBundle, formFor, loadProgress, missingAnswers, newProgress, orderFor, saveProgress,
} from '../lib/study'
import type { Study, StudyProgress, StudyQuestion, StudyReport } from '../lib/study'
import type { TaskSubmission } from '../lib/tasks'
import type { PublicExercise, PublicTask } from '../lib/types'
import { TaskWorkspace } from './TaskPage'

// #/study/<id>            ask for the participant code
// #/study/<id>/<code>     consent -> background -> tasks -> honesty -> report
export default function StudyPage({ studyId, code }: { studyId: string; code?: string }) {
  const [study, setStudy] = useState<Study | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    fetch(`/studies/${studyId}/study.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Study ${studyId} was not found.`))))
      .then(setStudy, (e) => setError(e.message))
  }, [studyId])

  if (error) return <Shell><h1 className="text-lg font-semibold">{error}</h1></Shell>
  if (!study) return <Shell><p className="text-muted">Loading…</p></Shell>
  if (!code) return <EnterCode study={study} />
  if (!CODE_PATTERN.test(code)) return <Shell><h1 className="text-lg font-semibold">That participant code is not valid.</h1></Shell>
  return <Session key={code} study={study} code={code} />
}

function EnterCode({ study }: { study: Study }) {
  const [code, setCode] = useState('')
  return (
    <Shell>
      <h1 className="text-xl font-semibold">{study.title}</h1>
      <p className="mt-2 leading-[1.5] text-muted">Enter the participant code you were given.</p>
      <form className="mt-5 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (CODE_PATTERN.test(code)) location.hash = `#/study/${study.id}/${code}` }}>
        <input value={code} onChange={(e) => setCode(e.target.value.trim())} aria-label="Participant code" placeholder="e.g. p17"
          className="h-10 w-56 rounded-lg border border-line-strong px-3 outline-none focus:border-accent" />
        <button type="submit" disabled={!CODE_PATTERN.test(code)} className="h-10 rounded-lg bg-accent px-4 font-semibold text-white disabled:opacity-40">Start</button>
      </form>
    </Shell>
  )
}

function Session({ study, code }: { study: Study; code: string }) {
  const [p, setP] = useState<StudyProgress>(() => loadProgress(study.id, code) ?? newProgress())
  useEffect(() => saveProgress(study.id, code, p), [p, study, code])
  const order = orderFor(study, code)
  const update = (patch: Partial<StudyProgress>) => setP((x) => ({ ...x, ...patch }))

  if (p.stage === 'consent') {
    return (
      <Shell>
        <h1 className="text-xl font-semibold">{study.title}</h1>
        <p className="mt-1 text-sm text-muted">Participant {code} · about {study.estimated_minutes} minutes · {order.length} tasks</p>
        <div className="mt-5 flex flex-col gap-3 rounded-[10px] border border-line bg-white p-5 leading-[1.55]">
          {study.consent.map((c, i) => <p key={i}>{c}</p>)}
        </div>
        <button type="button" onClick={() => update({ stage: 'survey', consent_at: new Date().toISOString() })}
          className="mt-5 h-10 rounded-lg bg-accent px-5 font-semibold text-white">I agree, continue</button>
      </Shell>
    )
  }

  if (p.stage === 'survey') {
    return (
      <Questions title="About you" intro="This lets us compare results across experience levels. It is never linked to your name."
        questions={study.survey} answers={p.survey} onAnswer={(id, v) => setP((x) => ({ ...x, survey: { ...x.survey, [id]: v } }))}
        next="Start the tasks" onNext={() => update({ stage: 'tasks', index: 0 })} />
    )
  }

  if (p.stage === 'tasks') {
    const entry = order[p.index]
    return (
      <StudyTask key={`${entry.exercise}:${entry.task}`} exercise={entry.exercise} taskId={entry.task} code={code}
        progress={`Task ${p.index + 1} of ${order.length}`}
        onSubmit={(sub) => {
          const tasks = [...p.tasks.filter((t) => !(t.exercise_id === sub.exercise_id && t.task_id === sub.task_id)), sub]
          update(p.index + 1 < order.length ? { tasks, index: p.index + 1 } : { tasks, stage: 'honesty' })
        }} />
    )
  }

  if (p.stage === 'honesty') {
    return (
      <Questions title={study.end_title ?? 'Last questions'}
        intro={study.end_intro ?? 'Answering honestly does not change anything for you; it tells us which results to trust.'}
        questions={study.honesty} answers={p.honesty} onAnswer={(id, v) => setP((x) => ({ ...x, honesty: { ...x.honesty, [id]: v } }))}
        next="Finish and see my results" onNext={() => update({ stage: 'submitting' })} />
    )
  }

  if (p.stage === 'submitting') return <Submit study={study} code={code} progress={p} onDone={(report) => update({ stage: 'done', report })} />
  return <Report study={study} code={code} report={p.report!} />
}

function StudyTask({ exercise, taskId, code, progress, onSubmit }: {
  exercise: string
  taskId: string
  code: string
  progress: string
  onSubmit: (sub: TaskSubmission) => void
}) {
  const [loaded, setLoaded] = useState<{ ex: PublicExercise; files: CodeFile[] } | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { loadExercise(exercise).then(setLoaded, (e) => setError(String(e))) }, [exercise])
  if (error) return <Shell><h1 className="text-lg font-semibold">Could not load this task</h1><p className="mt-2 text-muted">{error}</p></Shell>
  if (!loaded) return <Shell><p className="text-muted">Loading {progress.toLowerCase()}…</p></Shell>
  const task = loaded.ex.tasks?.find((t: PublicTask) => t.id === taskId)
  if (!task) return <Shell><h1 className="text-lg font-semibold">{exercise} has no task {taskId}.</h1></Shell>
  return <TaskWorkspace ex={loaded.ex} files={loaded.files} task={task}
    study={{ scope: `study-${code}`, candidateId: code, progress, onSubmit }} />
}

function Questions({ title, intro, questions, answers, onAnswer, next, onNext }: {
  title: string
  intro: string
  questions: StudyQuestion[]
  answers: Record<string, string>
  onAnswer: (id: string, value: string) => void   // updates the latest state, not a stale copy
  next: string
  onNext: () => void
}) {
  const missing = missingAnswers(questions, answers)
  return (
    <Shell>
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-1 text-muted">{intro}</p>
      <div className="mt-5 flex flex-col gap-5">
        {questions.map((q) => (
          <fieldset key={q.id}>
            <legend className="mb-2 font-medium">{q.label}</legend>
            {q.type === 'choice' ? (
              <div className="flex flex-wrap gap-2">
                {q.options!.map((o) => (
                  <button key={o} type="button" onClick={() => onAnswer(q.id, o)}
                    className={`h-9 rounded-lg border px-3 text-[13px] ${answers[q.id] === o ? 'border-accent bg-accent-soft font-medium text-accent' : 'border-line-strong bg-white hover:border-ink'}`}>
                    {o}
                  </button>
                ))}
              </div>
            ) : (
              <textarea value={answers[q.id] ?? ''} onChange={(e) => onAnswer(q.id, e.target.value)}
                className="h-20 w-full rounded-lg border border-line-strong px-2.5 py-2 text-[13px] outline-none focus:border-accent" />
            )}
          </fieldset>
        ))}
      </div>
      <button type="button" disabled={missing.length > 0} onClick={onNext}
        className="mt-6 h-10 rounded-lg bg-accent px-5 font-semibold text-white disabled:opacity-40">{next}</button>
    </Shell>
  )
}

function Submit({ study, code, progress, onDone }: { study: Study; code: string; progress: StudyProgress; onDone: (r: StudyReport) => void }) {
  const [state, setState] = useState<'sending' | 'offline' | 'error'>('sending')
  const [message, setMessage] = useState('')
  const bundle = buildBundle(study, code, progress)
  const send = async () => {
    setState('sending')
    try {
      const r = await fetch(`/api/study/${study.id}/submissions`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(bundle),
      })
      if (r.ok) return onDone(await r.json())
      const detail = await r.json().catch(() => null)
      setMessage(detail?.detail ?? `The server answered ${r.status}.`)
      setState(r.status >= 500 || r.status === 404 ? 'offline' : 'error')
    } catch {
      setState('offline')
    }
  }
  useEffect(() => { send() }, [])
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' }))
    const a = Object.assign(document.createElement('a'), { href: url, download: `readcode-${study.id}-${code}.json` })
    a.click()
    URL.revokeObjectURL(url)
  }
  return (
    <Shell>
      <h1 className="text-xl font-semibold">{state === 'sending' ? 'Sending your answers…' : 'Your answers are saved in this browser'}</h1>
      {state !== 'sending' && (
        <>
          <p className="mt-2 leading-[1.5] text-muted">
            {state === 'offline' ? 'We could not reach the study server.' : message} Download your results file and send it to the study organiser, or try again.
          </p>
          <div className="mt-5 flex gap-2">
            <button type="button" onClick={download} className="h-10 rounded-lg bg-accent px-4 font-semibold text-white">Download results file</button>
            <button type="button" onClick={send} className="h-10 rounded-lg border border-line-strong bg-white px-4 font-medium hover:border-ink">Try again</button>
          </div>
        </>
      )}
      <p className="mt-6 text-xs text-muted">Form {formFor(study, code)} · {progress.tasks.length} tasks answered</p>
    </Shell>
  )
}

function Report({ study, code, report }: { study: Study; code: string; report: StudyReport }) {
  const c = report.comparison
  return (
    <Shell>
      <h1 className="text-xl font-semibold">Your results</h1>
      <p className="mt-1 text-sm text-muted">{study.title} · participant {code}</p>
      <div className="mt-5 grid grid-cols-3 gap-3">
        <Stat label="Your score" value={`${Math.round(report.percent)}%`} />
        <Stat label={`Median, ${c.level}`} value={c.level_median != null ? `${Math.round(c.level_median)}%` : 'not enough yet'} />
        <Stat label="Better than" value={c.percentile != null ? `${c.percentile}% of others` : 'not enough yet'} />
      </div>
      <div className="mt-5 overflow-hidden rounded-[10px] border border-line bg-white">
        {report.tasks.map((t) => (
          <div key={`${t.exercise}:${t.task}`} className="flex items-center gap-3 border-b border-line px-4 py-3 last:border-b-0">
            <div className="min-w-0 flex-1">
              <div className="truncate text-[13.5px] font-medium">{t.title}</div>
              <div className="mt-0.5 text-xs text-muted">
                {Object.entries(t.parts).map(([k, v]) => `${k} ${v > 0 ? '✓' : '✗'}`).join(' · ')}
                {t.skills.length ? ` · about: ${t.skills.join(', ')}` : ''}
              </div>
            </div>
            <span className="font-mono text-sm">{Math.round(t.score)}/{t.max}</span>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs leading-[1.5] text-muted">
        Comparisons appear once at least five people at your level have taken part. Thank you for helping.
      </p>
    </Shell>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[10px] border border-line bg-white p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  )
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas">
      <header className="flex h-14 items-center border-b border-line bg-white px-5"><Logo /></header>
      <div className="mx-auto max-w-[680px] px-4 py-10">{children}</div>
    </div>
  )
}
