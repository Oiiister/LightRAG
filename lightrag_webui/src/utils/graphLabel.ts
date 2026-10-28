const STABLE_GATE_ID = /^(GATE-(?:OR|AND))-[0-9a-f]{16}$/i

/**
 * Human-readable label for a graph node.
 *
 * Gate nodes keep their stable hashed id internally so edges, selection and
 * updates still target one exact gate. Only the rendered label drops the hash.
 */
export function formatGraphLabel(label: string): string {
  return label.replace(STABLE_GATE_ID, '$1')
}
