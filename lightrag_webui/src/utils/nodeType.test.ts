import { describe, expect, test } from 'bun:test'

import {
  isFaultEventType,
  isLogicGateType,
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

  test('recognizes the ontology and localized logic-gate spellings', () => {
    expect(isLogicGateType('LogicGate')).toBe(true)
    expect(isLogicGateType('logic_gate')).toBe(true)
    expect(isLogicGateType('逻辑门')).toBe(true)
    expect(isLogicGateType('FaultEvent')).toBe(false)
    expect(isLogicGateType(undefined)).toBe(false)
  })
})
