// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { describe, expect, it } from 'vitest'
import { emailSchema, isValidEmail, optionalEmailSchema } from '@/lib/validation'

describe('validation', () => {
  it('isValidEmail', () => {
    expect(isValidEmail('a@b.co')).toBe(true)
    expect(isValidEmail('a@b')).toBe(false)
    expect(isValidEmail('a b@c.de')).toBe(false)
  })

  it('emailSchema requires a valid email', () => {
    expect(emailSchema.safeParse('a@b.co').success).toBe(true)
    expect(emailSchema.safeParse('').success).toBe(false)
    expect(emailSchema.safeParse('nope').success).toBe(false)
  })

  it('optionalEmailSchema allows empty and undefined', () => {
    expect(optionalEmailSchema.safeParse('').success).toBe(true)
    expect(optionalEmailSchema.safeParse(undefined).success).toBe(true)
    expect(optionalEmailSchema.safeParse('nope').success).toBe(false)
  })
})
