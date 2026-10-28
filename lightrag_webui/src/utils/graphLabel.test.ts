import { describe, expect, test } from 'bun:test'

import { formatGraphLabel } from './graphLabel'

describe('formatGraphLabel', () => {
  test('hides the stable hash on OR and AND gates', () => {
    expect(formatGraphLabel('GATE-OR-9333dd5903b9cf4a')).toBe('GATE-OR')
    expect(formatGraphLabel('GATE-AND-3b200c5f5a430e84')).toBe('GATE-AND')
  })

  test('leaves ordinary and partially matching names unchanged', () => {
    expect(formatGraphLabel('浮点例外')).toBe('浮点例外')
    expect(formatGraphLabel('GATE-OR')).toBe('GATE-OR')
    expect(formatGraphLabel('GATE-OR-custom')).toBe('GATE-OR-custom')
  })
})
