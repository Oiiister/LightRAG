import { describe, expect, test } from 'bun:test'

import {
  canLoadGraphView,
  isInvalidFaultRootResponse,
  isMissingFaultRootResponse,
  resolveGraphViewRoot
} from './graphViewSelection'

describe('graph view selection', () => {
  test('requires a root only for the causal view', () => {
    expect(canLoadGraphView('fault-causes', '*')).toBe(false)
    expect(canLoadGraphView('fault-causes', '冷却能力不足')).toBe(true)
    expect(canLoadGraphView('equipment-faults', '*')).toBe(true)
  })

  test('does not use the all-labels sentinel as a view root', () => {
    expect(resolveGraphViewRoot('fault-causes', '*')).toBeNull()
    expect(resolveGraphViewRoot('equipment-faults', '*')).toBeNull()
    expect(resolveGraphViewRoot('fault-causes', '冷却能力不足')).toBe(
      '冷却能力不足'
    )
  })

  test('recognizes only the backend FaultEvent rejection as a root type error', () => {
    const detail =
      '400 Bad Request\n{"detail":"fault-causes root must be a FaultEvent"}'
    expect(isInvalidFaultRootResponse(400, detail)).toBe(true)
    expect(isInvalidFaultRootResponse(404, detail)).toBe(false)
    expect(
      isInvalidFaultRootResponse(
        400,
        '{"detail":"fault-causes root must be found"}'
      )
    ).toBe(false)
  })

  test('distinguishes a missing root from a wrong root type', () => {
    const missing =
      '404 Not Found\n{"detail":"graph view root \'冷却能力不足\' was not found"}'
    expect(isMissingFaultRootResponse(404, missing)).toBe(true)
    expect(isMissingFaultRootResponse(400, missing)).toBe(false)
    expect(
      isMissingFaultRootResponse(
        404,
        '{"detail":"fault-causes root must be a FaultEvent"}'
      )
    ).toBe(false)
  })
})
