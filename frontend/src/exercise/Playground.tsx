import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { playground } from '../lib/playground'
import type { PlaygroundState } from '../lib/playground'
import type { PlaygroundPreset } from '../lib/types'

// The backend console: what a backend engineer looks at on call. Requests and
// responses, the external system's view, database rows, webhooks, logs, plus
// the levers to reproduce a failure (faults, clock).
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
  const [table, setTable] = useState('charges')

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

  const btn = 'h-8 rounded-md border border-code-border px-2.5 text-[12px] text-code-text hover:border-code-text disabled:opacity-40'
  const field = 'w-full rounded-md border border-code-border bg-code-bg px-2 py-1.5 font-mono text-[12px] text-code-text outline-none focus:border-code-text'
  const ready = !!sid && !busy
  return (
    <main className="flex min-w-0 flex-1 overflow-hidden bg-code-bg text-code-text">
      {/* Controls */}
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

        <Section title="Faults (next card network call)">
          {([['timeout_after_charge', 'Charge the card, then time out'], ['crash_after_charge', 'Charge the card, then the server dies']] as const).map(([k, label]) => (
            <label key={k} className="flex items-center gap-2 text-[12.5px]">
              <input type="checkbox" checked={!!state?.faults[k]} disabled={!ready}
                onChange={(e) => run(() => playground.faults(sid!, { [k]: e.target.checked }))} />
              {label}
            </label>
          ))}
        </Section>

        <Section title={`Clock · ${state ? state.clock.slice(11, 19) : '—'} UTC`}>
          <div className="flex gap-1.5">
            {([[60, '+1 min'], [600, '+10 min'], [3600, '+1 hour'], [86400, '+1 day']] as const).map(([s, l]) => (
              <button key={l} type="button" className={btn} disabled={!ready} onClick={() => run(() => playground.clock(sid!, s))}>{l}</button>
            ))}
          </div>
        </Section>

        <Section title="Webhook worker">
          <div className="flex flex-wrap gap-1.5">
            {[200, 404, 500].map((code) => (
              <button key={code} type="button" className={btn} disabled={!ready} onClick={() => run(() => playground.deliver(sid!, code))}>
                Run, endpoint answers {code}
              </button>
            ))}
          </div>
        </Section>

        <button type="button" onClick={reset} disabled={busy} className={btn}>Reset playground</button>
        {error && <p className="rounded-md bg-[rgba(248,81,73,0.18)] px-2.5 py-2 text-[12px]">{error}</p>}
      </div>

      {/* What you can observe */}
      <div className="grid min-w-0 flex-1 grid-cols-2 grid-rows-[auto_1fr] gap-3 overflow-y-auto p-4">
        <Panel title={`Response${state?.response ? ` · ${state.response.status}` : ''}`}>
          <pre className="whitespace-pre-wrap font-mono text-[11.5px]">{state?.response ? JSON.stringify(state.response.body, null, 2) : 'Send a request.'}</pre>
        </Panel>
        <Panel title={`Card network (what the bank saw) · total authorized ${state ? money(state.card_network.total_authorized) : ''}`}>
          {state?.card_network.authorizations.length
            ? <Rows rows={state.card_network.authorizations.map((a) => ({ id: a.id, amount: money(a.amount), reference: a.reference }))} />
            : <Empty>No authorizations yet.</Empty>}
        </Panel>
        <Panel title="Database">
          <div className="mb-2 flex flex-wrap gap-1">
            {Object.keys(state?.tables ?? {}).map((t) => (
              <button key={t} type="button" onClick={() => setTable(t)}
                className={`rounded px-2 py-0.5 font-mono text-[11px] ${t === table ? 'bg-code-fold text-code-text' : 'text-code-dim hover:text-code-text'}`}>
                {t} ({state!.tables[t].length})
              </button>
            ))}
          </div>
          {state?.tables[table]?.length ? <Rows rows={state.tables[table]} /> : <Empty>Empty.</Empty>}
        </Panel>
        <Panel title="Webhooks sent">
          {state?.webhooks.length
            ? <Rows rows={state.webhooks.map((w) => ({ type: w.type, to: w.url, reply: w.reply }))} />
            : <Empty>None yet. Run the webhook worker.</Empty>}
        </Panel>
        <div className="col-span-2">
          <Panel title="Logs">
            <pre className="max-h-[260px] overflow-y-auto whitespace-pre-wrap font-mono text-[11.5px] leading-5">
              {state?.logs.map((l, i) => (
                <div key={i} className={/fault|<- 5|<- 4/.test(l) ? 'text-[#ffa198]' : /card network/.test(l) ? 'text-code-pre' : ''}>{l}</div>
              ))}
            </pre>
          </Panel>
        </div>
      </div>
    </main>
  )
}

const money = (minor: number) => `$${(minor / 100).toFixed(2)}`

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

function Empty({ children }: { children: ReactNode }) {
  return <div className="text-[12px] text-code-dim">{children}</div>
}

function Rows({ rows }: { rows: Record<string, unknown>[] }) {
  const cols = Object.keys(rows[0])
  return (
    <div className="overflow-x-auto">
      <table className="w-full font-mono text-[11px]">
        <thead><tr>{cols.map((c) => <th key={c} className="pr-3 text-left font-normal text-code-dim">{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{cols.map((c) => <td key={c} className="max-w-[220px] truncate pr-3" title={String(r[c] ?? '')}>{String(r[c] ?? '')}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
