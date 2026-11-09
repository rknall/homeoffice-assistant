import type { EngineInterface, Register } from 'claude-code'

import { parseProgress } from './progress'
import type { Progress } from './progress'

const PANE = 'hoa-progress'
const TITLE = 'Pipeline progress'

// ponytail: newest ledger by mtime picks the active task; add a pin if several run at once
const loadProgress = async ($: EngineInterface): Promise<Progress | undefined> => {
  const entries = await $.fs.list('docs/specs').catch(() => [])
  let best: { slug: string; mtime: number } | undefined
  for (const entry of entries) {
    if (entry.kind !== 'dir') continue
    const path = `docs/specs/${entry.name}/work/ledger.md`
    const stat = await $.fs.stat(path).catch(() => undefined)
    if (stat && (!best || stat.mtimeMs > best.mtime)) best = { slug: entry.name, mtime: stat.mtimeMs }
  }
  if (!best) return undefined
  const ledger = await $.fs.read(`docs/specs/${best.slug}/work/ledger.md`)
  const plan = await $.fs.read(`docs/specs/${best.slug}/plan.md`).catch(() => '')
  return parseProgress(ledger, plan)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'pipeline-progress', description: 'Show the hoa-pipeline task progress in a side panel' })
    if (await $.fs.exists('docs/specs')) void $.ui.open({ id: PANE, title: TITLE })
    $.clock.every(15000, () => $.ui.invalidate('ui.render'))
    return next(e)
  })

  on('command.run', { command: 'pipeline-progress' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    return { text: 'Pipeline progress panel opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const p = await loadProgress($).catch(() => undefined)
    if (!p) return <Text dimColor>No pipeline ledger under docs/specs/.</Text>

    const done = p.waves.filter(w => w.verified).length
    const sliceTotal = p.waves.reduce((n, w) => n + w.slices.length, 0)
    const sliceDone = p.waves.reduce((n, w) => n + w.done.length, 0)
    const todo = p.waves.filter(w => !w.verified)

    return (
      <Box flexDirection="column">
        <Text weight="bold">{p.slug}</Text>
        <Text dimColor>{p.branch}</Text>
        <Text> </Text>
        <Text weight="bold">Stages</Text>
        {p.stages.map(s => (
          <Text dimColor={s.state === 'todo'} color={s.state === 'now' ? 'yellow' : undefined}>
            {s.state === 'done' ? 'done ' : s.state === 'now' ? 'now  ' : 'todo '}{s.name}
          </Text>
        ))}
        <Text> </Text>
        <Text weight="bold">Done</Text>
        <Text>
          {done}/{p.waves.length} waves verified, {sliceDone}/{sliceTotal} slices
        </Text>
        <Text> </Text>
        <Text weight="bold">Running</Text>
        {p.running.length === 0 && <Text dimColor>nothing</Text>}
        {p.running.slice(0, 8).map(k => <Text color="yellow">{k}</Text>)}
        <Text> </Text>
        <Text weight="bold">Still to do</Text>
        {todo.slice(0, 6).map(w => (
          <Text dimColor={w.done.length === 0}>
            wave {w.n}: {w.done.length}/{w.slices.length}{w.done.length === w.slices.length ? ', verify' : ''}
          </Text>
        ))}
        {todo.length > 6 && <Text dimColor>+{todo.length - 6} more waves</Text>}
        {p.stages.filter(s => s.state !== 'done' && s.name !== 'Implement').map(s => (
          <Text dimColor>{s.name}</Text>
        ))}
        <Text> </Text>
        <Text dimColor>{p.rulings} rulings in ledger</Text>
      </Box>
    )
  })
}
