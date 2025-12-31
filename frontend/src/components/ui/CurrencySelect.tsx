// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { forwardRef, type SelectHTMLAttributes, useEffect, useState } from 'react'
import { api } from '@/api/client'
import { cn } from '@/lib/utils'
import type { Currency } from '@/types'

interface CurrencySelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string
  error?: string
}

export const CurrencySelect = forwardRef<HTMLSelectElement, CurrencySelectProps>(
  ({ className, label, error, id, value, ...props }, ref) => {
    const [currencies, setCurrencies] = useState<Currency[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
      api
        .get<Currency[]>('/currencies')
        .then((data) => {
          setCurrencies(data)
          setLoading(false)
        })
        .catch((err) => {
          console.error('Failed to load currencies:', err)
          // Fallback to common currencies if API fails
          setCurrencies([
            { code: 'EUR', name: 'Euro' },
            { code: 'USD', name: 'United States Dollar' },
            { code: 'GBP', name: 'British Pound' },
            { code: 'CHF', name: 'Swiss Franc' },
            { code: 'PLN', name: 'Polish Złoty' },
          ])
          setLoading(false)
        })
    }, [])

    const selectId = id || props.name

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={selectId} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          disabled={loading}
          value={value ?? ''}
          className={cn(
            'block w-full rounded-lg bg-white px-3 py-2.5 pr-10',
            'border border-gray-300 shadow-sm',
            'text-gray-900',
            'transition-all duration-150 ease-in-out',
            'hover:border-gray-400',
            'focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none',
            'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            'appearance-none bg-no-repeat bg-right',
            'bg-[url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 fill=%27none%27 viewBox=%270 0 20 20%27%3E%3Cpath stroke=%27%236b7280%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27 stroke-width=%271.5%27 d=%27M6 8l4 4 4-4%27/%3E%3C/svg%3E")] bg-[length:1.5rem_1.5rem] bg-[right_0.5rem_center]',
            error &&
              'border-red-500 hover:border-red-500 focus:border-red-500 focus:ring-red-500/20',
            className,
          )}
          {...props}
        >
          {loading ? (
            <>
              <option value="">Loading currencies...</option>
              {/* Include current value as option during loading to maintain selection */}
              {value && <option value={value as string}>{value}</option>}
            </>
          ) : (
            <>
              <option value="" disabled>
                Select currency
              </option>
              {currencies.map((currency) => (
                <option key={currency.code} value={currency.code}>
                  {currency.code} - {currency.name}
                </option>
              ))}
            </>
          )}
        </select>
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>
    )
  },
)

CurrencySelect.displayName = 'CurrencySelect'
