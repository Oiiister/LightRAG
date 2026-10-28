export type FaultDepthStyle = {
  band: number
  color: string
  size: number
}

export const FAULT_DEPTH_STYLES: ReadonlyArray<FaultDepthStyle> = [
  { band: 0, color: '#991b1b', size: 28 },
  { band: 1, color: '#dc2626', size: 23 },
  { band: 2, color: '#f97316', size: 19 },
  { band: 3, color: '#eab308', size: 16 },
  { band: 4, color: '#0ea5e9', size: 13 },
  { band: 5, color: '#7c3aed', size: 11 }
]

const FAULT_ENTITY_TYPES = new Set([
  'fault',
  'faultevent',
  '故障',
  '故障事件'
])

export const resolveFaultDepthStyle = (
  entityType: unknown,
  viewDepth: unknown
): FaultDepthStyle | null => {
  if (typeof entityType !== 'string') return null
  const normalizedType = entityType.toLowerCase().replace(/\s+/g, '')
  if (!FAULT_ENTITY_TYPES.has(normalizedType)) return null

  const numericDepth = Number(viewDepth)
  const depth =
    Number.isFinite(numericDepth) && numericDepth >= 0
      ? Math.floor(numericDepth)
      : 0
  return FAULT_DEPTH_STYLES[
    Math.min(depth, FAULT_DEPTH_STYLES.length - 1)
  ]
}
