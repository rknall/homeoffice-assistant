// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { z } from 'zod'

/**
 * Email regex pattern - matches standard email format
 */
export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * Required email schema - validates that the value is a valid email address
 */
export const emailSchema = z
  .string()
  .min(1, 'Email is required')
  .refine((val) => EMAIL_REGEX.test(val), {
    message: 'Please enter a valid email address',
  })

/**
 * Optional email schema - allows empty string or valid email
 * Use this for fields where email is not required
 */
export const optionalEmailSchema = z
  .string()
  .refine((val) => val === '' || EMAIL_REGEX.test(val), {
    message: 'Please enter a valid email address',
  })
  .optional()

/**
 * Validates an email address
 * @param email - The email address to validate
 * @returns true if valid, false otherwise
 */
export function isValidEmail(email: string): boolean {
  return EMAIL_REGEX.test(email)
}
