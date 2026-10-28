import { describe, expect, test } from 'bun:test'
import { UndirectedGraph } from 'graphology'

import {
  applyCausalLayeredPositions,
  type CausalLayoutNodeAttributes
} from './causalGraphLayout'

type TestEdgeAttributes = {
  relation?: string
}

const addNode = (
  graph: UndirectedGraph<CausalLayoutNodeAttributes, TestEdgeAttributes>,
  id: string,
  depth: number,
  nodeType: string
) => {
  graph.addNode(id, {
    x: 0,
    y: 0,
    viewDepth: depth,
    nodeType
  })
}

describe('causal graph layout', () => {
  test('keeps inputs to the same logic gate adjacent and centred below it', () => {
    const graph = new UndirectedGraph<
      CausalLayoutNodeAttributes,
      TestEdgeAttributes
    >()
    addNode(graph, 'fault-root', 0, 'FaultEvent')
    addNode(graph, 'gate-z', 1, 'LogicGate')
    addNode(graph, 'gate-a', 1, '逻辑门')
    addNode(graph, 'input-z', 2, 'FaultEvent')
    addNode(graph, 'input-a', 2, 'FaultEvent')
    addNode(graph, 'input-y', 2, 'FaultEvent')
    addNode(graph, 'input-b', 2, 'FaultEvent')

    graph.addEdge('fault-root', 'gate-z')
    graph.addEdge('fault-root', 'gate-a')
    graph.addEdge('gate-z', 'input-z')
    graph.addEdge('gate-z', 'input-a')
    graph.addEdge('gate-a', 'input-y')
    graph.addEdge('gate-a', 'input-b')

    applyCausalLayeredPositions(graph)

    const x = (node: string) => graph.getNodeAttribute(node, 'x')
    const y = (node: string) => graph.getNodeAttribute(node, 'y')

    expect((x('input-a') + x('input-z')) / 2).toBe(x('gate-z'))
    expect((x('input-b') + x('input-y')) / 2).toBe(x('gate-a'))
    expect(Math.abs(x('input-a') - x('input-z'))).toBe(6)
    expect(Math.abs(x('input-b') - x('input-y'))).toBe(6)
    const leftGate =
      x('gate-a') < x('gate-z') ? 'gate-a' : 'gate-z'
    const leftInputs =
      leftGate === 'gate-a' ? ['input-b', 'input-y'] : ['input-a', 'input-z']
    const rightInputs =
      leftGate === 'gate-a' ? ['input-a', 'input-z'] : ['input-b', 'input-y']
    expect(Math.max(...leftInputs.map(x))).toBeLessThan(
      Math.min(...rightInputs.map(x))
    )
    expect([y('fault-root'), y('gate-z'), y('input-a')]).toEqual([0, -6, -12])
  })

  test('prefers a connected logic gate over another preceding-depth neighbour', () => {
    const graph = new UndirectedGraph<
      CausalLayoutNodeAttributes,
      TestEdgeAttributes
    >()
    addNode(graph, 'fault-root', 0, 'FaultEvent')
    addNode(graph, 'gate', 1, 'LogicGate')
    addNode(graph, 'rule', 1, 'FaultCauseRule')
    addNode(graph, 'shared-input', 2, 'FaultEvent')

    graph.addEdge('fault-root', 'gate')
    graph.addEdge('fault-root', 'rule')
    graph.addEdge('gate', 'shared-input')
    graph.addEdge('rule', 'shared-input')

    applyCausalLayeredPositions(graph)

    expect(graph.getNodeAttribute('shared-input', 'x')).toBe(
      graph.getNodeAttribute('gate', 'x')
    )
  })
})
