// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Link } from 'react-router-dom'
import type { EventsByStatus } from '@/types'

interface StatsRowProps {
  stats: EventsByStatus
}

interface StatCardProps {
  label: string
  count: number
  color: 'blue' | 'amber' | 'slate'
  filterValue: string
}

function StatCard({ label, count, color, filterValue }: StatCardProps) {
  const colorClasses = {
    blue: 'border-l-blue-500 bg-blue-50/50',
    amber: 'border-l-amber-500 bg-amber-50/50',
    slate: 'border-l-slate-400 bg-slate-50/50',
  }

  const countClasses = {
    blue: 'text-blue-700',
    amber: 'text-amber-700',
    slate: 'text-slate-600',
  }

  return (
    <Link
      to={`/events?status=${filterValue}`}
      className={`
        flex-1 px-4 py-3 rounded-lg border-l-4 transition-all
        hover:shadow-md hover:scale-[1.02]
        ${colorClasses[color]}
      `}
    >
      <div className={`text-2xl font-bold ${countClasses[color]}`}>{count}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </Link>
  )
}

export function StatsRow({ stats }: StatsRowProps) {
  return (
    <div className="flex gap-4">
      <StatCard label="Active Events" count={stats.active} color="blue" filterValue="active" />
      <StatCard label="Upcoming" count={stats.upcoming} color="amber" filterValue="upcoming" />
      <StatCard label="Past Events" count={stats.past} color="slate" filterValue="past" />
    </div>
  )
}
