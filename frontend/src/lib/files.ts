// Loading an exercise's code files and preparing each one for display
// (lines, highlighting, outline). Exercises can have several files.
import { highlightFor } from './highlight'
import type { Token } from './highlight'
import { outlineFor } from './outline'
import type { OutlineSection } from './outline'
import type { PublicExercise } from './types'

export interface CodeFile {
  path: string
  language: string
  lines: string[]
  tokens: Token[][]
  sections: OutlineSection[]
}

export function languageOf(path: string): string {
  if (/\.py$/.test(path)) return 'python'
  if (/\.[ch]$/.test(path)) return 'c'
  return 'text'
}

export function prepareFile(path: string, source: string): CodeFile {
  const language = languageOf(path)
  const text = source.replace(/\r\n/g, '\n').replace(/\n$/, '')
  const lines = text.split('\n')
  return { path, language, lines, tokens: highlightFor(language, text), sections: outlineFor(language, lines) }
}

// The file to open first: the first one in the exercise's own language that has
// an outline (e.g. app.py rather than README.md or __init__.py).
export function primaryFile(ex: PublicExercise, files: CodeFile[]): CodeFile {
  return files.find((f) => f.language === ex.language && f.sections.length > 0) ?? files[0]
}

export async function loadExercise(id: string): Promise<{ ex: PublicExercise; files: CodeFile[] }> {
  const res = await fetch(`/exercises/${id}/public.json`)
  if (!res.ok) throw new Error(`Exercise ${id} was not found.`)
  const ex: PublicExercise = await res.json()
  const files = await Promise.all(ex.files.map(async (f) => {
    const r = await fetch(`/exercises/${id}/code/${f.path}`)
    if (!r.ok) throw new Error(`Could not load ${f.path}.`)
    return prepareFile(f.path, await r.text())
  }))
  return { ex, files }
}
