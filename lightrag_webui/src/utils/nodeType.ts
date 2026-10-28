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
