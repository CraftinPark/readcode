// Builds the sidebar outline from C source: banner comments become sections,
// column-0 function definitions become entries.

export interface OutlineFunction {
  name: string
  line: number
  end: number
}

export interface OutlineSection {
  title: string
  line: number
  functions: OutlineFunction[]
}

const RULE = /^\/\*\s*-{10,}\s*\*\/\s*$/
const BANNER = /^\/\*\s*(.+?)\s*\*\/\s*$/
const DEF_START = /^(?!typedef\b|struct\b|enum\b|union\b|#|\/\*|\s)[A-Za-z_][\w\s*]*?\b([A-Za-z_]\w*)\s*\(/

export function parseOutline(lines: string[]): OutlineSection[] {
  const sections: OutlineSection[] = []
  let current: OutlineSection | null = null

  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i]
    if (RULE.test(ln) && i + 1 < lines.length) {
      const m = BANNER.exec(lines[i + 1])
      if (m && !RULE.test(lines[i + 1])) {
        // "Internal helpers (caller must hold c->lock)" -> "Internal helpers"
        current = { title: m[1].replace(/\s*\(.*\)\s*$/, ''), line: i + 1, functions: [] }
        sections.push(current)
        i += 2
        continue
      }
    }
    const def = DEF_START.exec(ln)
    if (!def) continue
    // A definition reaches "{" before ";" (a prototype reaches ";" first).
    let j = i
    while (j < lines.length && !/[{;]\s*$/.test(lines[j])) j++
    if (j >= lines.length || /;\s*$/.test(lines[j])) continue
    let end = j
    while (end < lines.length && lines[end] !== '}') end++
    if (!current) {
      current = { title: 'Top of file', line: 1, functions: [] }
      sections.push(current)
    }
    current.functions.push({ name: def[1], line: i + 1, end: Math.min(end + 1, lines.length) })
    i = end
  }
  return sections
}

// Python: "# ----" / "# Title" / "# ----" banners become sections; top-level
// classes and functions become entries, and so do functions defined directly
// inside a top-level function (e.g. route handlers inside create_app).
// Methods of a class are left out, as their class already has an entry.
const PY_RULE = /^#\s*-{10,}\s*$/
const PY_BANNER = /^#\s*(\S.*?)\s*$/
const PY_DEF = /^( *)(?:async\s+)?(def|class)\s+([A-Za-z_]\w*)/

export function parsePythonOutline(lines: string[]): OutlineSection[] {
  const sections: OutlineSection[] = []
  let current: OutlineSection | null = null
  const indentOf = (ln: string) => ln.length - ln.trimStart().length
  const isCode = (ln: string) => ln.trim() !== '' && !ln.trimStart().startsWith('#')
  let parentKind: string | null = null    // kind of the enclosing top-level def/class

  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i]
    if (PY_RULE.test(ln) && i + 2 < lines.length && PY_RULE.test(lines[i + 2])) {
      const m = PY_BANNER.exec(lines[i + 1])
      if (m) {
        current = { title: m[1], line: i + 2, functions: [] }
        sections.push(current)
        i += 2
        continue
      }
    }
    const def = PY_DEF.exec(ln)
    if (!def) continue
    const indent = def[1].length
    if (indent === 0) parentKind = def[2]
    else if (!(indent === 4 && parentKind === 'def' && def[2] === 'def')) continue
    // The body ends before the next code line indented at or left of the def.
    let end = i + 1
    while (end < lines.length && !(isCode(lines[end]) && indentOf(lines[end]) <= indent)) end++
    while (end > i + 1 && lines[end - 1].trim() === '') end--
    // A decorator directly above belongs to this definition.
    let start = i
    while (start > 0 && lines[start - 1].trimStart().startsWith('@') && indentOf(lines[start - 1]) === indent) start--
    if (!current) {
      current = { title: 'Top of file', line: 1, functions: [] }
      sections.push(current)
    }
    current.functions.push({ name: def[3], line: start + 1, end })
  }
  return sections
}

export function outlineFor(language: string, lines: string[]): OutlineSection[] {
  return language === 'python' ? parsePythonOutline(lines) : parseOutline(lines)
}

export function allFunctions(sections: OutlineSection[]): OutlineFunction[] {
  return sections.flatMap((s) => s.functions)
}

// The innermost match wins (a Python handler sits inside create_app).
export function functionAt(sections: OutlineSection[], line: number): OutlineFunction | undefined {
  return allFunctions(sections)
    .filter((f) => f.line <= line && line <= f.end)
    .reduce<OutlineFunction | undefined>((best, f) => (!best || f.line > best.line ? f : best), undefined)
}
