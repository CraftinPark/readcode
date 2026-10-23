// Client for the backend playground (backend/playground): a running copy of an
// example's shipped code that the candidate can send requests to, break with
// faults, and inspect (logs, database rows, card network, webhooks).

export interface PlaygroundState {
  session?: string
  clock: string
  faults: { timeout_after_charge: boolean; crash_after_charge: boolean }
  card_network: {
    authorizations: { id: string; reference: string; amount: number; currency: string }[]
    refunds: { reference: string; authorization: string; amount: number }[]
    total_authorized: number
  }
  tables: Record<string, Record<string, unknown>[]>
  webhooks: { url: string; type: string; event: string; reply: number }[]
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
  faults: (sid: string, f: Partial<PlaygroundState['faults']>) => call(`/api/playground/sessions/${sid}/faults`, f),
  clock: (sid: string, seconds: number) => call(`/api/playground/sessions/${sid}/clock`, { seconds }),
  deliver: (sid: string, reply_status: number) => call(`/api/playground/sessions/${sid}/webhooks/deliver`, { reply_status }),
}
