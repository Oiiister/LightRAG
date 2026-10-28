const UNKNOWN_NODE_TYPE = 'Unknown'

export const resolveNodeType = (
  properties: Record<string, unknown> | null | undefined
): string => {
  const rawType = properties?.class_code ?? properties?.entity_type
  if (typeof rawType !== 'string') return UNKNOWN_NODE_TYPE
  return rawType.trim() || UNKNOWN_NODE_TYPE
}

export const isFaultEventType = (nodeType: unknown): boolean =>
  typeof nodeType === 'string' &&
  nodeType.toLowerCase().replace(/[\s_-]/g, '') === 'faultevent'

export const isLogicGateType = (nodeType: unknown): boolean => {
  if (typeof nodeType !== 'string') return false
  const normalized = nodeType.toLowerCase().replace(/[\s_-]/g, '')
  return normalized === 'logicgate' || normalized === '逻辑门'
}
