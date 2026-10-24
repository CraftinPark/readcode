import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import Ajv2020 from 'ajv/dist/2020'
import addFormats from 'ajv-formats'
import { describe, expect, it } from 'vitest'
import { highlightC, highlightFor } from './highlight'
import { allFunctions, functionAt, outlineFor, parseOutline, parsePythonOutline } from './outline'
import { buildSubmission } from './submission'
import { buildBundle, fnv1a, formFor, missingAnswers, newProgress, orderFor } from './study'
import type { Study } from './study'
import { languageOf, prepareFile, primaryFile } from './files'
import { buildTaskSubmission, canSubmitTask, taskTitle, ticketParts } from './tasks'
import type { TaskAnswer } from './tasks'
import type { Answers, PublicExercise } from './types'

const ROOT = resolve(__dirname, '../../..')
const EX = resolve(ROOT, 'examples/readcode-001')
const source = readFileSync(resolve(EX, 'code/lru_cache.c'), 'utf8')
const lines = source.split('\n')
const pub: PublicExercise = JSON.parse(readFileSync(resolve(EX, 'public.json'), 'utf8'))

describe('outline', () => {
  const sections = parseOutline(lines)

  it('finds the banner sections', () => {
    expect(sections.map((s) => s.title)).toEqual(['Types', 'Internal helpers', 'Public API', 'Demo driver'])
  })

  it('finds function definitions with their start lines', () => {
    const fns = Object.fromEntries(allFunctions(sections).map((f) => [f.name, f.line]))
    expect(fns).toMatchObject({ evict_tail: 185, lru_create: 209, lru_put: 257, lru_hit_ratio: 415, main: 466 })
    expect(fns).not.toHaveProperty('lru_evict_cb') // a typedef, not a function
  })

  it('maps a line to its function', () => {
    expect(functionAt(sections, 200)?.name).toBe('evict_tail')
    expect(functionAt(sections, 224)?.name).toBe('lru_create')
    expect(functionAt(sections, 30)).toBeUndefined()
  })
})

describe('highlight', () => {
  const tokens = highlightC(source)

  it('keeps every character and line', () => {
    expect(tokens.length).toBe(lines.length)
    tokens.forEach((t, i) => expect(t.map((x) => x.text).join('')).toBe(lines[i]))
  })

  it('colours keywords, constants and comments', () => {
    const kinds = (n: number) => Object.fromEntries(tokens[n - 1].map((t) => [t.text, t.kind]))
    expect(kinds(185)).toMatchObject({ static: 'kw', void: 'kw' })
    expect(kinds(29)['/* Types                                                              */']).toBe('com')
  })
})

describe('python outline and highlight', () => {
  const py = readFileSync(resolve(ROOT, 'examples/readcode-002/code/payments_api.py'), 'utf8')
  const pyLines = py.replace(/\n$/, '').split('\n')
  const sections = parsePythonOutline(pyLines)
  const fns = Object.fromEntries(allFunctions(sections).map((f) => [f.name, f]))

  it('finds the banner sections', () => {
    expect(sections.map((s) => s.title)).toEqual(['Storage', 'Request and response shapes', 'App'])
  })

  it('lists classes, functions and the handlers inside create_app, but not methods', () => {
    expect(Object.keys(fns)).toEqual(expect.arrayContaining(
      ['Account', 'Charge', 'Store', 'charge_json', 'create_app', 'load_charge', 'create_charge', 'list_charges', 'create_refund']))
    expect(fns).not.toHaveProperty('next_seq')
    expect(fns).not.toHaveProperty('refunded')
  })

  it('starts a handler at its decorator and maps lines inside it', () => {
    expect(pyLines[fns.create_refund.line - 1].trim()).toBe('@app.post("/charges/{charge_id}/refunds")')
    expect(functionAt(sections, fns.create_refund.line + 8)?.name).toBe('create_refund')
    expect(functionAt(sections, fns.load_charge.line + 2)?.name).toBe('load_charge')
  })

  it('picks the parser by language', () => {
    expect(outlineFor('python', pyLines).map((s) => s.title)).toContain('App')
    expect(outlineFor('c', lines).map((s) => s.title)).toContain('Public API')
  })

  it('keeps every character and colours python tokens', () => {
    const tokens = highlightFor('python', py.replace(/\n$/, ''))
    expect(tokens.length).toBe(pyLines.length)
    tokens.forEach((t, i) => expect(t.map((x) => x.text).join('')).toBe(pyLines[i]))
    const n = pyLines.findIndex((l) => l.includes('def load_charge'))
    expect(Object.fromEntries(tokens[n].map((t) => [t.text, t.kind]))).toMatchObject({ def: 'kw' })
    const docEnd = pyLines.indexOf('"""')
    for (let i = 0; i <= docEnd; i++) {                    // the whole module docstring is one string
      tokens[i].forEach((t) => expect(t.kind).toBe('str'))
    }
    expect(tokens[n - 1].some((t) => t.kind === 'pre') || pyLines[n - 1].trim() === '').toBe(true)
  })
})

describe('multi-file exercises and tasks', () => {
  const EX3 = resolve(ROOT, 'examples/readcode-003')
  const pub3: PublicExercise = JSON.parse(readFileSync(resolve(EX3, 'public.json'), 'utf8'))
  const files = pub3.files.map((f) => prepareFile(f.path, readFileSync(resolve(EX3, 'code', f.path), 'utf8')))

  it('prepares every file and opens the main code file first', () => {
    files.forEach((f, i) => expect(f.lines.length).toBe(pub3.files[i].line_count))
    expect(languageOf('README.md')).toBe('text')
    expect(files.find((f) => f.path === 'README.md')!.sections).toEqual([])
    expect(primaryFile(pub3, files).path).toBe('payments/app.py')
  })

  it('titles tickets and splits out the customer quote', () => {
    const t1 = pub3.tasks!.find((t) => t.id === 'T1')!
    expect(taskTitle(t1)).toBe('Support ticket #5120 (Acme)')
    const { from, quote, ask } = ticketParts(t1)
    expect(from).toBe('Support ticket #5120 (Acme)')
    expect(quote).toMatch(/^A customer was charged twice/)
    expect(ask).toMatch(/^Find the cause/)
  })

  it('builds task submissions that match the schema', () => {
    const schema = JSON.parse(readFileSync(resolve(ROOT, 'schemas/task-submission.schema.json'), 'utf8'))
    const ajv = new Ajv2020({ allErrors: true })
    addFormats(ajv)
    const validate = ajv.compile(schema)
    const t1 = pub3.tasks!.find((t) => t.id === 'T1')!
    const t5 = pub3.tasks!.find((t) => t.id === 'T5')!
    const a: TaskAnswer = { startedAt: Date.parse('2026-10-22T10:00:00Z'), answers: {}, ranges: [{ file: 'payments/app.py', start_line: 91, end_line: 91 }],
      explanation: '  random reference  ', fix: '' }
    expect(canSubmitTask(t1, a)).toBe(true)
    expect(canSubmitTask(t1, { ...a, ranges: [] })).toBe(false)
    const sub = buildTaskSubmission(pub3, t1, a, 'local', new Date('2026-10-22T10:09:00Z'))
    expect(validate(sub)).toBe(true)
    expect(sub).toMatchObject({ task_id: 'T1', task_type: 'incident', explanation: 'random reference', time_spent_minutes: 9 })
    expect(canSubmitTask(t5, { ...a, ranges: [] })).toBe(false)              // a review needs a verdict
    const review = buildTaskSubmission(pub3, t5, { ...a, ranges: [], verdict: 'request_changes' }, 'local')
    expect(validate(review)).toBe(true)
    expect(sub).not.toHaveProperty('confidence')
  })

  it('submits multiple-choice answers only when every part is answered', () => {
    const schema = JSON.parse(readFileSync(resolve(ROOT, 'schemas/task-submission.schema.json'), 'utf8'))
    const ajv = new Ajv2020({ allErrors: true })
    addFormats(ajv)
    const validate = ajv.compile(schema)
    const pub4: PublicExercise = JSON.parse(readFileSync(resolve(ROOT, 'examples/readcode-004/public.json'), 'utf8'))
    const t1 = pub4.tasks![0]
    expect(t1.parts!.map((p) => p.id)).toEqual(['where', 'why', 'fix'])
    const a: TaskAnswer = { startedAt: Date.now(), answers: { where: 'b', why: 'b' }, ranges: [], explanation: '', fix: '' }
    expect(canSubmitTask(t1, a)).toBe(false)
    const done = { ...a, answers: { ...a.answers, fix: 'c' } }
    expect(canSubmitTask(t1, done)).toBe(true)
    const sub = buildTaskSubmission(pub4, t1, done, 'local')
    expect(sub.answers).toEqual({ where: 'b', why: 'b', fix: 'c' })
    expect(sub).not.toHaveProperty('explanation')
    expect(validate(sub)).toBe(true)
  })
})

describe('study mode', () => {
  const study: Study = JSON.parse(readFileSync(resolve(ROOT, 'studies/pilot-1/study.json'), 'utf8'))

  it('hashes codes exactly like the backend', () => {
    // Same reference values as backend/tests/test_study.py.
    expect(['p01', 'syn001', 'alice-7', ''].map(fnv1a)).toEqual([723412596, 3238330556, 2566655595, 2166136261])
  })

  it('gives each code one form, warm-up tasks first, the rest shuffled but stable', () => {
    for (const code of ['p01', 'p02', 'syn001', 'alice-7']) {
      const form = study.forms[formFor(study, code)]
      const order = orderFor(study, code)
      expect(order.slice(0, study.fixed_first)).toEqual(form.slice(0, study.fixed_first))
      expect([...order].map((t) => `${t.exercise}:${t.task}`).sort()).toEqual(form.map((t) => `${t.exercise}:${t.task}`).sort())
      expect(orderFor(study, code)).toEqual(order)
    }
    expect(new Set(['p01', 'p02', 'p03', 'p04', 'p05', 'p06'].map((c) => formFor(study, c))).size).toBe(2)
  })

  it('needs every required answer and builds a bundle for the server', () => {
    expect(missingAnswers(study.survey, {})).toContain('years')
    const p = { ...newProgress(), consent_at: '2026-11-01T10:00:00Z', survey: { years: '2-5' } }
    const b = buildBundle(study, 'p01', p)
    expect(b).toMatchObject({ study_id: 'pilot-1', participant: 'p01', form: formFor(study, 'p01'), consent_at: '2026-11-01T10:00:00Z' })
    expect(b.order).toHaveLength(study.forms[b.form].length)
  })
})

describe('submission', () => {
  const schema = JSON.parse(readFileSync(resolve(ROOT, 'schemas/submission.schema.json'), 'utf8'))
  const ajv = new Ajv2020({ allErrors: true })
  addFormats(ajv)
  const validate = ajv.compile(schema)

  const answers: Answers = {
    startedAt: Date.parse('2026-10-13T10:00:00Z'),
    comprehension: { C1: 'A hash table and a list.', C2: '   ' },
    design: { D1: 'Shard it.' },
    comments: [
      { id: 'c1', type: 'bug', ranges: [{ file: 'lru_cache.c', start_line: 198, end_line: 202 }], text: 'use after free',
        severity: 'critical', confidence: 'certain', fix: 'call back first', function: 'evict_tail' },
      { id: 'c2', type: 'question', ranges: [{ file: 'lru_cache.c', start_line: 10, end_line: 10 }], text: 'why?' },
      { id: 'c3', type: 'design', ranges: [{ file: 'lru_cache.c', start_line: 20, end_line: 22 }], text: 'global lock' },
      { id: 'c4', type: 'improvement', ranges: [{ file: 'lru_cache.c', start_line: 30, end_line: 30 }], text: 'add remove_entry()' },
      { id: 'c5', type: 'bug', ranges: [{ file: 'lru_cache.c', start_line: 40, end_line: 40 }], text: '  ' },
    ],
    improvements: [{ id: 'i1', title: 'Add tests', detail: '' }],
  }
  const sub = buildSubmission(pub, answers, 'local', new Date('2026-10-13T10:30:00Z'))

  it('matches submission.schema.json', () => {
    expect(validate(sub), JSON.stringify(validate.errors)).toBe(true)
  })

  it('maps comment types to the right sections and drops blanks', () => {
    expect(sub.comprehension).toEqual({ C1: 'A hash table and a list.' })
    expect(sub.bugs.map((b) => b.id)).toEqual(['c1'])
    expect(sub.notes.map((n) => [n.id, n.type])).toEqual([['c2', 'question'], ['c3', 'design']])
    expect(sub.improvements.map((i) => i.title)).toEqual(['Add tests', 'add remove_entry()'])
    expect(sub.time_spent_minutes).toBe(30)
  })

  it('validates an empty submission too', () => {
    const empty = buildSubmission(pub, { ...answers, comprehension: {}, design: {}, comments: [], improvements: [] }, 'x')
    expect(validate(empty), JSON.stringify(validate.errors)).toBe(true)
  })
})
