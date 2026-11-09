import { expect, test } from 'claude-code/testing'

import { parseProgress } from './progress'

const PLAN = '### Wave 0\n**s1 A** - x\n**s2 B** - y\n### Wave 1\n**s3 C** - z\n'
const LEDGER = [
  'slug: demo',
  'work branch: audit/demo',
  'dispatch plan r1 opus',
  'plan r1 opus: DONE p.md -> plan-review',
  'plan-review r1 opus: DONE r.md -> implement waves',
  'dispatch implement r1 w0 s1 haiku',
  'implement r1 w0 s1 haiku: DONE a.md -> wait',
  'dispatch implement r1 w0 s2 sonnet',
  'implement r1 w0 s2 sonnet: DONE b.md -> wave 0 complete',
  'implement-verify r1 w0 sonnet: DONE v.md -> next-wave',
  'dispatch implement r1 w1 s3 opus',
  'Ruling: something - why - cost',
].join('\n')

test('counts done slices, verified waves and running dispatches', async () => {
  const p = parseProgress(LEDGER, PLAN)
  expect(p.slug).toBe('demo')
  expect(p.waves.map(w => [w.done.length, w.slices.length, w.verified])).toEqual([
    [2, 2, true],
    [0, 1, false],
  ])
  expect(p.running).toEqual(['implement r1 w1 s3'])
  expect(p.stages.find(s => s.name === 'Implement')?.state).toBe('now')
  expect(p.stages.find(s => s.name === 'Review')?.state).toBe('todo')
  expect(p.rulings).toBe(1)
})
