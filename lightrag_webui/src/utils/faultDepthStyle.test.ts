import { describe, expect, test } from 'bun:test'

import {
  FAULT_DEPTH_STYLES,
  resolveFaultDepthStyle
} from '@/utils/faultDepthStyle'

describe('resolveFaultDepthStyle', () => {
  test('uses progressively smaller, distinct styles for fault depth', () => {
    const root = resolveFaultDepthStyle('FaultEvent', 0)
    const firstCause = resolveFaultDepthStyle('faultevent', 1)
    const secondCause = resolveFaultDepthStyle('故障事件', 2)

    expect(root?.color).toBe('#991b1b')
    expect(firstCause?.color).not.toBe(root?.color)
    expect(secondCause?.color).not.toBe(firstCause?.color)
    expect(root!.size).toBeGreaterThan(firstCause!.size)
    expect(firstCause!.size).toBeGreaterThan(secondCause!.size)
  })

  test('caps deeper causes at the final depth band', () => {
    expect(resolveFaultDepthStyle('FaultEvent', 99)).toEqual(
      FAULT_DEPTH_STYLES[FAULT_DEPTH_STYLES.length - 1]
    )
  })

  test('does not restyle non-fault nodes', () => {
    expect(resolveFaultDepthStyle('LogicGate', 0)).toBeNull()
    expect(resolveFaultDepthStyle('Equipment', 0)).toBeNull()
  })
})
