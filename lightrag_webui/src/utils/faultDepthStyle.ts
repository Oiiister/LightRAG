export type FaultDepthStyle = {
  band: number
  color: string
  size: number
}

export const LOGIC_GATE_NODE_SIZE = 16

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

const LOGIC_GATE_ENTITY_TYPES = new Set([
  'logicgate',
  '逻辑门'
])

const normalizeFaultViewType = (entityType: unknown): string | null =>
  typeof entityType === 'string'
    ? entityType.toLowerCase().replace(/\s+/g, '')
    : null

export const resolveFaultDepthStyle = (
  entityType: unknown,
  viewDepth: unknown
): FaultDepthStyle | null => {
  const normalizedType = normalizeFaultViewType(entityType)
  if (normalizedType === null) return null
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

/**
 * Size for a node in the fault-causes view.
 *
 * Fault events still shrink by causal depth, while every logic gate uses one
 * fixed size. Without that override, LogicGate falls back to degree scaling:
 * a central OR gate with many inputs becomes much larger than a leaf OR gate.
 */
export const resolveFaultViewNodeSize = (
  entityType: unknown,
  viewDepth: unknown,
  fallbackSize: number
): number => {
  const depthStyle = resolveFaultDepthStyle(entityType, viewDepth)
  if (depthStyle) return depthStyle.size

  const normalizedType = normalizeFaultViewType(entityType)
  return normalizedType !== null && LOGIC_GATE_ENTITY_TYPES.has(normalizedType)
    ? LOGIC_GATE_NODE_SIZE
    : fallbackSize
}
