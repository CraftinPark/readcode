import { forwardRef } from 'react'
import type { OutlineSection } from '../lib/outline'

interface Props {
  files: { path: string; comments: number }[]
  activeFile: string
  onOpenFile: (path: string) => void
  sections: OutlineSection[]
  currentFn: string | undefined
  savedCount: Map<string, number>
  draftFn: string | undefined
  query: string
  hitInfo: string
  onQuery: (q: string) => void
  onNextHit: (back: boolean) => void
  onJump: (line: number) => void
}

export const Sidebar = forwardRef<HTMLInputElement, Props>(function Sidebar(p, searchRef) {
  return (
    <aside className="flex w-56 flex-none flex-col gap-1.5 overflow-y-auto border-r border-line bg-panel px-3 py-4">
      <div className="relative mb-2">
        <input ref={searchRef} type="search" aria-label="Search code" placeholder="Search code (Ctrl+F)" value={p.query}
          onChange={(e) => p.onQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); p.onNextHit(e.shiftKey) }
            if (e.key === 'Escape') p.onQuery('')
          }}
          className="h-[34px] w-full rounded-lg border border-line-strong bg-white px-2.5 text-[13px] outline-none focus:border-accent" />
        {p.query && <div className="mt-1 px-1 text-[11px] text-muted">{p.hitInfo}</div>}
      </div>
      {p.files.length > 1 && (
        <>
          <div className="px-2 pb-1 text-[11px] font-semibold tracking-[0.06em] text-muted">FILES</div>
          <div className="mb-3 flex flex-col gap-0.5">
            {p.files.map((f) => {
              const slash = f.path.lastIndexOf('/')
              const active = f.path === p.activeFile
              return (
                <button key={f.path} type="button" onClick={() => p.onOpenFile(f.path)} title={f.path}
                  className={`flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left font-mono text-[12.5px] text-ink ${active ? 'bg-accent-soft font-medium' : 'hover:bg-chip'}`}>
                  <span className="truncate">
                    {slash >= 0 && <span className="text-muted">{f.path.slice(0, slash + 1)}</span>}
                    {f.path.slice(slash + 1)}
                  </span>
                  {f.comments > 0 && (
                    <b className="min-w-4 rounded-lg bg-accent px-[5px] py-px text-center font-sans text-[11px] font-semibold text-white">{f.comments}</b>
                  )}
                </button>
              )
            })}
          </div>
        </>
      )}
      <div className="px-2 pb-1 text-[11px] font-semibold tracking-[0.06em] text-muted">OUTLINE</div>
      {p.sections.length === 0 && <div className="px-2 py-1 text-[12.5px] text-muted">No outline for this file.</div>}
      {p.sections.map((s) => (
        <div key={s.line} className="flex flex-col gap-0.5">
          <button type="button" onClick={() => p.onJump(s.line)}
            className="w-full rounded-md px-2 py-1.5 text-left text-[12.5px] text-ink hover:bg-chip">
            {s.title}
          </button>
          {s.functions.map((f) => {
            const active = f.name === p.currentFn
            const saved = p.savedCount.get(f.name) ?? 0
            const drafting = p.draftFn === f.name
            return (
              <button key={f.name} type="button" onClick={() => p.onJump(f.line)}
                className={`flex w-full items-center justify-between rounded-md py-1.5 pl-4 pr-2 text-left font-mono text-[12.5px] text-ink ${active ? 'bg-accent-soft font-medium' : 'hover:bg-chip'}`}>
                <span className="truncate">{f.name}</span>
                <span className="flex items-center gap-1.5 text-muted">
                  {f.line}
                  {(saved > 0 || drafting) && (
                    <b className={`min-w-4 rounded-lg px-[5px] py-px text-center font-sans text-[11px] font-semibold ${drafting ? 'bg-bug text-ink' : 'bg-accent text-white'}`}>
                      {saved + (drafting ? 1 : 0)}
                    </b>
                  )}
                </span>
              </button>
            )
          })}
        </div>
      ))}
      <div className="flex-1" />
      <div className="mt-3 rounded-lg border border-line bg-white p-2.5 text-xs leading-[1.45] text-muted">
        <b className="font-semibold text-ink">Tip</b>
        <br />
        Drag across line numbers to select a range, then describe what is wrong and why it fails. Shift-click extends a selection.
      </div>
    </aside>
  )
})
