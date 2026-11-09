// Pure parsing of a hoa-pipeline ledger and plan into a progress summary.

export type Wave = { n: number; slices: string[]; done: string[]; verified: boolean }
export type Stage = { name: string; state: 'done' | 'now' | 'todo' }
export type Progress = {
  slug: string
  branch: string
  stages: Stage[]
  waves: Wave[]
  running: string[]
  rulings: number
}

const MODEL = /^(opus|sonnet|haiku)$/

// "implement r4 w2 s9 sonnet (note)" -> "implement r4 w2 s9"
const keyOf = (text: string): string => {
  const out: string[] = []
  for (const tok of text.trim().split(/\s+/)) {
    if (MODEL.test(tok.replace(/[:,]$/, ''))) break
    out.push(tok)
  }
  return out.join(' ')
}

export const parsePlanWaves = (plan: string): { n: number; slices: string[] }[] => {
  const waves: { n: number; slices: string[] }[] = []
  for (const line of plan.split('\n')) {
    const w = line.match(/^### Wave (\d+)/)
    if (w) {
      waves.push({ n: Number(w[1]), slices: [] })
      continue
    }
    const s = line.match(/^\*\*(s\d+[a-z]?) /)
    if (s && waves.length > 0) waves[waves.length - 1].slices.push(s[1])
  }
  return waves
}

export const parseProgress = (ledger: string, plan: string): Progress => {
  const lines = ledger.split('\n').map(l => l.trim()).filter(Boolean)
  const field = (name: string) =>
    lines.find(l => l.startsWith(`${name}:`))?.slice(name.length + 1).trim() ?? '?'

  const results = lines.filter(
    l => !l.startsWith('dispatch ') && / (DONE|INCOMPLETE|FAILURE)\b/.test(l),
  )
  const resultKeys = new Set(results.map(l => keyOf(l.split(':')[0])))
  const dispatches = lines.filter(l => l.startsWith('dispatch ')).map(l => keyOf(l.slice(9)))
  const running = [...new Set(dispatches.filter(k => !resultKeys.has(k)))]

  const doneSlices = new Map<number, Set<string>>()
  const verifiedWaves = new Set<number>()
  for (const l of results) {
    if (!/: DONE\b/.test(l)) continue
    const v = l.match(/^implement-verify r\d+ w(\d+)/)
    if (v) verifiedWaves.add(Number(v[1]))
    const m = l.match(/^implement r\d+ w(\d+) (s\d+[a-z]?)/)
    if (m) {
      const set = doneSlices.get(Number(m[1])) ?? new Set<string>()
      set.add(m[2])
      doneSlices.set(Number(m[1]), set)
    }
  }
  const waves: Wave[] = parsePlanWaves(plan).map(w => ({
    ...w,
    done: w.slices.filter(s => doneSlices.get(w.n)?.has(s) ?? false),
    verified: verifiedWaves.has(w.n),
  }))

  const has = (re: RegExp) => results.some(l => re.test(l))
  const seen = (re: RegExp) => lines.some(l => re.test(l))
  const allVerified = waves.length > 0 && waves.every(w => w.verified)
  const flags: [string, boolean, boolean][] = [
    ['Investigation', seen(/^plan r\d/), seen(/^(dispatch )?(sub-)?investigation/)],
    ['Plan + review', seen(/^plan-review r\d+ .*-> implement/), seen(/^(dispatch )?plan/)],
    ['Implement', allVerified, seen(/^(dispatch )?implement/)],
    ['Refactor', has(/^refactor r\d+ .*: DONE/), seen(/^(dispatch )?refactor r\d/)],
    ['Review', has(/^review r\d+ .*: DONE .*-> present/), seen(/^(dispatch )?review r\d/)],
    ['Present', has(/^present r\d+ .*: DONE/), seen(/^(dispatch )?present r\d/)],
  ]
  const stages: Stage[] = flags.map(([name, isDone, isStarted]) => ({
    name,
    state: isDone ? 'done' : isStarted ? 'now' : 'todo',
  }))

  return {
    slug: field('slug'),
    branch: field('work branch'),
    stages,
    waves,
    running,
    rulings: lines.filter(l => l.startsWith('Ruling')).length,
  }
}
