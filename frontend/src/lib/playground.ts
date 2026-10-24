// Client for the backend playground (backend/playground): a running copy of an
// example's shipped code. The server describes its own controls and panels, so
// one console works for every example.

export interface PlaygroundControl {
  id: string
  label: string
  kind: 'button' | 'toggle' | 'datetime' | 'note'
  on?: boolean
}

export interface PlaygroundState {
  session?: string
  clock: string
  controls: { group: string; items: PlaygroundControl[] }[]
  panels: { id: string; title: string; rows: Record<string, unknown>[] }[]
  logs: string[]
  response?: { status: number; body: unknown }
}

async function call(url: string, body?: unknown): Promise<PlaygroundState> {
  const r = await fetch(url, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!r.ok) {
    const detail = await r.json().catch(() => null)
    throw new Error(detail?.detail ?? `The playground answered ${r.status}. Is it running? (cd backend && python -m playground)`)
  }
  return r.json()
}

export const playground = {
  start: (example: string) => call(`/api/playground/${example}/sessions`, {}),
  request: (sid: string, req: { method: string; path: string; headers: Record<string, string>; body?: unknown }) =>
    call(`/api/playground/sessions/${sid}/request`, req),
  act: (sid: string, action: string, value?: unknown) => call(`/api/playground/sessions/${sid}/act`, { action, value }),
}
