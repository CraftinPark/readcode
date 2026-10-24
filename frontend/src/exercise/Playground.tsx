import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { playground } from '../lib/playground'
import type { PlaygroundControl, PlaygroundState } from '../lib/playground'
import type { PlaygroundPreset } from '../lib/types'

// The backend console: what a backend engineer looks at on call. Requests and
// responses, database rows, what external systems saw, logs; plus the levers
// to reproduce a failure. The server says which controls and panels exist.
export function Playground({ example, presets }: { example: string; presets: PlaygroundPreset[] }) {
  const [sid, setSid] = useState<string | null>(null)
  const [state, setState] = useState<PlaygroundState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [preset, setPreset] = useState(0)
  const [method, setMethod] = useState(presets[0].method)
  const [path, setPath] = useState(presets[0].path)
  const [headers, setHeaders] = useState(JSON.stringify(presets[0].headers ?? {}, null, 2))
  const [body, setBody] = useState(presets[0].body ? JSON.stringify(presets[0].body, null, 2) : '')
  const [when, setWhen] = useState('')
  const [panel, setPanel] = useState<string | null>(null)

  const run = async (f: () => Promise<PlaygroundState>) => {
    setBusy(true)
    setError(null)
    try {
      const s = await f()
      if (s.session) setSid(s.session)
      setState(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }
  const reset = () => run(() => playground.start(example))
  useEffect(() => { reset() }, [example])
  useEffect(() => { if (state && !when) setWhen(state.clock.slice(0, 16)) }, [state])

  const pick = (i: number) => {
    const p = presets[i]
    setPreset(i)
    setMethod(p.method)
    setPath(p.path)
    setHeaders(JSON.stringify(p.headers ?? {}, null, 2))
    setBody(p.body ? JSON.stringify(p.body, null, 2) : '')
  }
  const send = () => {
    let h: Record<string, string>, b: unknown
    try {
      h = JSON.parse(headers || '{}')
      b = method === 'POST' && body.trim() ? JSON.parse(body) : undefined
    } catch {
      setError('Headers and body must be valid JSON.')
      return
    }
    run(() => playground.request(sid!, { method, path, headers: h, body: b }))
  }
  const act = (c: PlaygroundControl, value?: unknown) => run(() => playground.act(sid!, c.id, value))

  const btn = 'min-h-8 rounded-md border border-code-border px-2.5 py-1 text-left text-[12px] text-code-text hover:border-code-text disabled:opacity-40'
  const field = 'w-full rounded-md border border-code-border bg-code-bg px-2 py-1.5 font-mono text-[12px] text-code-text outline-none focus:border-code-text'
  const ready = !!sid && !busy
  const shown = state?.panels.find((p) => p.id === panel) ?? state?.panels[0]
  return (
    <main className="flex min-w-0 flex-1 overflow-hidden bg-code-bg text-code-text">
      <div className="flex w-[340px] flex-none flex-col gap-4 overflow-y-auto border-r border-code-border p-4">
        <Section title="Request">
          <div className="flex flex-wrap gap-1.5">
            {presets.map((p, i) => (
              <button key={p.label} type="button" onClick={() => pick(i)}
                className={`${btn} ${i === preset ? 'border-code-text' : ''}`}>{p.label}</button>
            ))}
          </div>
          <div className="mt-2 flex gap-1.5">
            <select value={method} onChange={(e) => setMethod(e.target.value as 'GET' | 'POST')} className={`${field} w-20`}>
              <option>POST</option><option>GET</option>
            </select>
            <input value={path} onChange={(e) => setPath(e.target.value)} className={field} aria-label="Path" />
          </div>
          <label className="mt-2 block text-[11px] text-code-dim">Headers
            <textarea value={headers} onChange={(e) => setHeaders(e.target.value)} rows={3} className={field} />
          </label>
          {method === 'POST' && (
            <label className="mt-1 block text-[11px] text-code-dim">Body
              <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} className={field} />
            </label>
          )}
          <button type="button" onClick={send} disabled={!ready}
            className="mt-2 h-8 w-full rounded-md bg-accent text-[13px] font-semibold text-white disabled:opacity-40">Send</button>
        </Section>

        {state?.controls.map((g) => (
          <Section key={g.group} title={g.group === 'Clock' ? `Clock · ${state.clock.slice(0, 16).replace('T', ' ')} UTC` : g.group}>
            <div className="flex flex-wrap gap-1.5">
              {g.items.map((c) => c.kind === 'toggle' ? (
                <label key={c.id} className="flex w-full items-center gap-2 text-[12.5px]">
                  <input type="checkbox" checked={!!c.on} disabled={!ready} onChange={(e) => act(c, e.target.checked)} />
                  {c.label}
                </label>
              ) : c.kind === 'datetime' ? (
                <div key={c.id} className="flex w-full gap-1.5">
                  <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className={field} aria-label={c.label} />
                  <button type="button" className={btn} disabled={!ready || !when} onClick={() => act(c, `${when}:00Z`)}>Set</button>
                </div>
              ) : c.kind === 'note' ? (
                <span key={c.id} className="text-[12px] text-code-dim">{c.label}</span>
              ) : (
                <button key={c.id} type="button" className={btn} disabled={!ready} onClick={() => act(c)}>{c.label}</button>
              ))}
            </div>
          </Section>
        ))}

        <button type="button" onClick={reset} disabled={busy} className={btn}>Reset playground</button>
        {error && <p className="rounded-md bg-[rgba(248,81,73,0.18)] px-2.5 py-2 text-[12px]">{error}</p>}
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-3 overflow-y-auto p-4">
        <Panel title={`Response${state?.response ? ` · ${state.response.status}` : ''}`}>
          <pre className="max-h-[220px] overflow-y-auto whitespace-pre-wrap font-mono text-[11.5px]">
            {state?.response ? JSON.stringify(state.response.body, null, 2) : 'Send a request.'}
          </pre>
        </Panel>
        <Panel title="Data">
          <div className="mb-2 flex flex-wrap gap-1">
            {state?.panels.map((p) => (
              <button key={p.id} type="button" onClick={() => setPanel(p.id)}
                className={`rounded px-2 py-0.5 text-[11.5px] ${p.id === shown?.id ? 'bg-code-fold text-code-text' : 'text-code-dim hover:text-code-text'}`}>
                {p.title} ({p.rows.length})
              </button>
            ))}
          </div>
          {shown?.rows.length ? <Rows rows={shown.rows} /> : <div className="text-[12px] text-code-dim">Empty.</div>}
        </Panel>
        <Panel title="Logs">
          <pre className="max-h-[280px] overflow-y-auto whitespace-pre-wrap font-mono text-[11.5px] leading-5">
            {state?.logs.map((l, i) => (
              <div key={i} className={/fault|<- 5|<- 4/.test(l) ? 'text-[#ffa198]' : /provider|card network|webhook/.test(l) ? 'text-code-pre' : ''}>{l}</div>
            ))}
          </pre>
        </Panel>
      </div>
    </main>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-2 text-[11px] font-semibold tracking-[0.06em] text-code-dim">{title.toUpperCase()}</div>
      {children}
    </div>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-w-0 rounded-lg border border-code-border bg-code-bar p-3">
      <div className="mb-2 text-[11px] font-semibold tracking-[0.06em] text-code-dim">{title.toUpperCase()}</div>
      {children}
    </div>
  )
}

function Rows({ rows }: { rows: Record<string, unknown>[] }) {
  const cols = Object.keys(rows[0])
  return (
    <div className="overflow-x-auto">
      <table className="w-full font-mono text-[11px]">
        <thead><tr>{cols.map((c) => <th key={c} className="pr-3 text-left font-normal text-code-dim">{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{cols.map((c) => <td key={c} className="max-w-[200px] truncate pr-3" title={String(r[c] ?? '')}>{String(r[c] ?? '')}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
