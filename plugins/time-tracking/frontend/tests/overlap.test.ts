// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Tests for time overlap detection logic
 *
 * This tests the timesOverlap function used in UnifiedTimeTrackingPage
 * to detect overlapping time entries across companies.
 */

import { describe, expect, it } from 'vitest'

/**
 * Check if two time ranges overlap.
 * Times are in HH:MM format.
 * Copied from UnifiedTimeTrackingPage for testing.
 */
function timesOverlap(start1: string, end1: string, start2: string, end2: string): boolean {
  const toMinutes = (time: string): number => {
    const [h, m] = time.split(':').map(Number)
    return h * 60 + m
  }

  let start1Mins = toMinutes(start1)
  let end1Mins = toMinutes(end1)
  let start2Mins = toMinutes(start2)
  let end2Mins = toMinutes(end2)

  // Handle overnight shifts
  const range1Overnight = end1Mins < start1Mins
  const range2Overnight = end2Mins < start2Mins

  if (range1Overnight) end1Mins += 24 * 60
  if (range2Overnight) end2Mins += 24 * 60

  // Adjust for overnight comparisons
  if (range1Overnight && !range2Overnight) {
    const originalEnd1 = toMinutes(end1)
    if (start2Mins < originalEnd1) {
      start2Mins += 24 * 60
      end2Mins += 24 * 60
    }
  }

  if (range2Overnight && !range1Overnight) {
    const originalEnd2 = toMinutes(end2)
    if (start1Mins < originalEnd2) {
      start1Mins += 24 * 60
      end1Mins += 24 * 60
    }
  }

  return start1Mins < end2Mins && start2Mins < end1Mins
}

describe('Time Overlap Detection', () => {
  describe('Basic overlaps', () => {
    it('should detect overlapping ranges', () => {
      // 09:00-12:00 and 11:00-14:00 overlap
      expect(timesOverlap('09:00', '12:00', '11:00', '14:00')).toBe(true)
    })

    it('should detect one range containing another', () => {
      // 08:00-17:00 contains 10:00-12:00
      expect(timesOverlap('08:00', '17:00', '10:00', '12:00')).toBe(true)
    })

    it('should detect identical ranges', () => {
      expect(timesOverlap('09:00', '17:00', '09:00', '17:00')).toBe(true)
    })
  })

  describe('Non-overlapping ranges', () => {
    it('should detect non-overlapping consecutive ranges', () => {
      // 09:00-12:00 and 12:00-14:00 (adjacent, not overlapping)
      expect(timesOverlap('09:00', '12:00', '12:00', '14:00')).toBe(false)
    })

    it('should detect non-overlapping separate ranges', () => {
      // 09:00-12:00 and 14:00-17:00 (gap between)
      expect(timesOverlap('09:00', '12:00', '14:00', '17:00')).toBe(false)
    })

    it('should handle morning and evening shifts', () => {
      // Morning: 06:00-10:00, Evening: 18:00-22:00
      expect(timesOverlap('06:00', '10:00', '18:00', '22:00')).toBe(false)
    })
  })

  describe('Edge cases', () => {
    it('should handle same start time', () => {
      expect(timesOverlap('09:00', '12:00', '09:00', '10:00')).toBe(true)
    })

    it('should handle same end time', () => {
      expect(timesOverlap('09:00', '12:00', '11:00', '12:00')).toBe(true)
    })

    it('should handle short ranges', () => {
      // 30-minute meeting overlap
      expect(timesOverlap('09:00', '09:30', '09:15', '09:45')).toBe(true)
    })
  })

  describe('Overnight shifts', () => {
    it('should handle overnight shift (22:00-06:00)', () => {
      // Night shift 22:00-06:00 overlaps with early morning 05:00-08:00
      expect(timesOverlap('22:00', '06:00', '05:00', '08:00')).toBe(true)
    })

    it('should handle overnight shift not overlapping with morning', () => {
      // Night shift 22:00-02:00 doesn't overlap with 08:00-12:00
      expect(timesOverlap('22:00', '02:00', '08:00', '12:00')).toBe(false)
    })

    it('should handle two overnight shifts overlapping', () => {
      // 22:00-06:00 and 23:00-07:00
      expect(timesOverlap('22:00', '06:00', '23:00', '07:00')).toBe(true)
    })

    it('should handle overnight shift overlapping with late evening', () => {
      // Night shift 22:00-06:00 overlaps with 20:00-23:00
      expect(timesOverlap('22:00', '06:00', '20:00', '23:00')).toBe(true)
    })
  })

  describe('Real-world scenarios', () => {
    it('should detect part-time jobs overlapping', () => {
      // Company A: 08:00-12:00, Company B: 11:30-15:30
      expect(timesOverlap('08:00', '12:00', '11:30', '15:30')).toBe(true)
    })

    it('should allow sequential part-time jobs', () => {
      // Company A: 08:00-12:00, Company B: 13:00-17:00
      expect(timesOverlap('08:00', '12:00', '13:00', '17:00')).toBe(false)
    })

    it('should detect lunch meeting overlapping with work', () => {
      // Work: 09:00-17:00, External meeting: 12:00-13:30
      expect(timesOverlap('09:00', '17:00', '12:00', '13:30')).toBe(true)
    })
  })
})

describe('Time conversion helpers', () => {
  describe('toMinutes helper', () => {
    const toMinutes = (time: string): number => {
      const [h, m] = time.split(':').map(Number)
      return h * 60 + m
    }

    it('should convert midnight to 0', () => {
      expect(toMinutes('00:00')).toBe(0)
    })

    it('should convert noon to 720', () => {
      expect(toMinutes('12:00')).toBe(720)
    })

    it('should convert 23:59 to 1439', () => {
      expect(toMinutes('23:59')).toBe(1439)
    })

    it('should handle leading zeros', () => {
      expect(toMinutes('09:05')).toBe(545)
    })
  })
})
