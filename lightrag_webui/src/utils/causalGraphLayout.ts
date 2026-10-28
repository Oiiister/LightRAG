import type { UndirectedGraph } from 'graphology'

import { isLogicGateType } from '@/utils/nodeType'

export type CausalLayoutNodeAttributes = {
  x: number
  y: number
  viewDepth?: number
  nodeType?: string
}

const NODE_SPACING = 6
const DEPTH_SPACING = 6

const compareNodeIds = (left: string, right: string): number =>
  left.localeCompare(right)

const readDepth = <
  NodeAttributes extends CausalLayoutNodeAttributes,
  EdgeAttributes extends Record<string, any>
>(
  graph: UndirectedGraph<NodeAttributes, EdgeAttributes>,
  node: string
): number => {
  const depth = Number(graph.getNodeAttribute(node, 'viewDepth') ?? 0)
  return Number.isFinite(depth) ? Math.max(0, Math.floor(depth)) : 0
}

/**
 * Position the fault-causes DAG as a deterministic forest.
 *
 * A causal node belongs to the nearest LogicGate on the preceding depth when
 * one is connected; otherwise its parent is the first preceding-depth
 * neighbour. Every parent is centred over its direct children and each child
 * reserves the horizontal span of its own descendants. This keeps all inputs
 * to one gate adjacent wherever the graph remains a tree and gives a stable
 * best effort when one node feeds multiple gates.
 */
export const applyCausalLayeredPositions = <
  NodeAttributes extends CausalLayoutNodeAttributes,
  EdgeAttributes extends Record<string, any>
>(
  graph: UndirectedGraph<NodeAttributes, EdgeAttributes>
): void => {
  if (graph.order === 0) return

  const depthByNode = new Map<string, number>()
  for (const node of graph.nodes()) {
    depthByNode.set(node, readDepth(graph, node))
  }

  const parentByNode = new Map<string, string>()
  for (const node of graph.nodes()) {
    let bestGate: string | null = null
    let bestNeighbour: string | null = null
    const depth = depthByNode.get(node) ?? 0

    for (const neighbour of graph.neighbors(node)) {
      if (depthByNode.get(neighbour) !== depth - 1) continue
      if (
        bestNeighbour === null ||
        compareNodeIds(neighbour, bestNeighbour) < 0
      ) {
        bestNeighbour = neighbour
      }
      if (
        isLogicGateType(graph.getNodeAttribute(neighbour, 'nodeType')) &&
        (bestGate === null || compareNodeIds(neighbour, bestGate) < 0)
      ) {
        bestGate = neighbour
      }
    }

    const parent = bestGate ?? bestNeighbour
    if (parent !== null) parentByNode.set(node, parent)
  }

  const childrenByParent = new Map<string, string[]>()
  for (const [node, parent] of parentByNode) {
    const children = childrenByParent.get(parent) ?? []
    children.push(node)
    childrenByParent.set(parent, children)
  }
  for (const children of childrenByParent.values()) {
    children.sort(compareNodeIds)
  }

  const halfWidthByNode = new Map<string, number>()
  const measure = (node: string): number => {
    const measured = halfWidthByNode.get(node)
    if (measured !== undefined) return measured

    const children = childrenByParent.get(node) ?? []
    if (children.length === 0) {
      halfWidthByNode.set(node, 0)
      return 0
    }

    let childSpan = (children.length - 1) * NODE_SPACING
    for (const child of children) {
      childSpan += 2 * measure(child)
    }
    const halfWidth = childSpan / 2
    halfWidthByNode.set(node, halfWidth)
    return halfWidth
  }

  const place = (node: string, centerX: number): void => {
    const depth = depthByNode.get(node) ?? 0
    graph.setNodeAttribute(node, 'x', centerX)
    graph.setNodeAttribute(node, 'y', depth === 0 ? 0 : -depth * DEPTH_SPACING)

    const children = childrenByParent.get(node) ?? []
    if (children.length === 0) return

    let childSpan = (children.length - 1) * NODE_SPACING
    for (const child of children) {
      childSpan += 2 * measure(child)
    }
    let cursor = centerX - childSpan / 2
    for (const child of children) {
      const halfWidth = measure(child)
      place(child, cursor + halfWidth)
      cursor += 2 * halfWidth + NODE_SPACING
    }
  }

  const roots = graph
    .nodes()
    .filter((node) => !parentByNode.has(node))
    .sort((left, right) => {
      const depthDifference =
        (depthByNode.get(left) ?? 0) - (depthByNode.get(right) ?? 0)
      return depthDifference || compareNodeIds(left, right)
    })

  let forestSpan = (roots.length - 1) * NODE_SPACING
  for (const root of roots) {
    forestSpan += 2 * measure(root)
  }
  let cursor = -forestSpan / 2
  for (const root of roots) {
    const halfWidth = measure(root)
    place(root, cursor + halfWidth)
    cursor += 2 * halfWidth + NODE_SPACING
  }
}
