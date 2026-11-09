// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { FieldErrors, UseFormRegister } from 'react-hook-form'
import { CurrencySelect } from '@/components/ui/CurrencySelect'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { categoryOptions, type ExpenseForm, paymentTypeOptions } from './expenseForm'

interface ExpenseFormFieldsProps {
  register: UseFormRegister<ExpenseForm>
  errors: FieldErrors<ExpenseForm>
  currency: string
  gridGap: 'gap-3' | 'gap-4'
}

/** Date, amount, currency, payment type, category and description inputs. */
export function ExpenseFormFields({ register, errors, currency, gridGap }: ExpenseFormFieldsProps) {
  return (
    <>
      <Input label="Date" type="date" {...register('date')} error={errors.date?.message} />
      <div className={`grid grid-cols-2 ${gridGap}`}>
        <Input
          label="Amount"
          type="number"
          step="0.01"
          {...register('amount')}
          error={errors.amount?.message}
        />
        <CurrencySelect
          label="Currency"
          value={currency}
          {...register('currency')}
          error={errors.currency?.message}
        />
      </div>
      <Select
        label="Payment Type"
        options={paymentTypeOptions}
        {...register('payment_type')}
        error={errors.payment_type?.message}
      />
      <Select
        label="Category"
        options={categoryOptions}
        {...register('category')}
        error={errors.category?.message}
      />
      <Input label="Description" {...register('description')} error={errors.description?.message} />
    </>
  )
}
