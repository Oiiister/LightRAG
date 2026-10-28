import { describe, expect, test } from 'bun:test'

import {
  isFaultEventType,
  resolveNodeType
} from './nodeType'

describe('node type display', () => {
  test('prefers the canonical class code over the extracted entity type', () => {
    expect(
      resolveNodeType({ class_code: 'FaultEvent', entity_type: 'Event' })
    ).toBe('FaultEvent')
  })

  test('falls back safely for malformed node properties', () => {
    expect(resolveNodeType({ class_code: { invalid: true } })).toBe('Unknown')
    expect(resolveNodeType(null)).toBe('Unknown')
  })

  test('recognizes only FaultEvent as the causal root type', () => {
    expect(isFaultEventType('FaultEvent')).toBe(true)
    expect(isFaultEventType('fault_event')).toBe(true)
    expect(isFaultEventType('Equipment')).toBe(false)
    expect(isFaultEventType(undefined)).toBe(false)
  })
})
