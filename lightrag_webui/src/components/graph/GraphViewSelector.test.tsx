import { beforeEach, describe, expect, test } from 'bun:test'
import { fireEvent, screen } from '@testing-library/react'

import GraphViewSelector from '@/components/graph/GraphViewSelector'
import { RawGraph, useGraphStore } from '@/stores/graph'
import { useSettingsStore } from '@/stores/settings'
import { renderWithProviders } from '@/test/render'

describe('GraphViewSelector', () => {
  beforeEach(() => {
    useGraphStore.setState({
      graphViewId: 'department-files',
      graphDataFetchAttempted: true,
      lastSuccessfulQueryLabel: '*',
      rawGraph: null
    })
    useSettingsStore.setState({ queryLabel: '*' })
  })

  test('switches projection and requests a refresh', () => {
    renderWithProviders(<GraphViewSelector />)

    fireEvent.click(screen.getByRole('button', { name: 'Department equipment' }))

    const state = useGraphStore.getState()
    expect(state.graphViewId).toBe('department-equipment')
    expect(state.graphDataFetchAttempted).toBe(false)
    expect(state.graphDataVersion).toBeGreaterThan(0)
  })

  test('fault causes explains that a FaultEvent root is required', () => {
    renderWithProviders(<GraphViewSelector />)

    fireEvent.click(screen.getByRole('button', { name: 'Fault causes' }))

    expect(useGraphStore.getState().graphViewId).toBe('fault-causes')
    expect(
      screen
        .getByText(
          'Select a FaultEvent in the label search to use it as the causal-graph root.'
        )
        .textContent
    ).toContain('FaultEvent')
  })

  test('fault causes shows the causal-depth color and size legend', () => {
    useSettingsStore.setState({ queryLabel: '出口压力不足' })
    useGraphStore.setState({ graphViewId: 'fault-causes' })
    renderWithProviders(<GraphViewSelector />)

    expect(screen.getByText('Root fault').textContent).toBe('Root fault')
    expect(screen.getByText('Level 1 cause').textContent).toBe('Level 1 cause')
    expect(screen.getByText('Level 5+ cause').textContent).toBe(
      'Level 5+ cause'
    )
  })

  test('does not switch to fault causes when the selected root is not a FaultEvent', () => {
    const rawGraph = new RawGraph()
    rawGraph.nodes = [
      {
        id: 'P-101A',
        labels: ['P-101A'],
        properties: {
          entity_id: 'P-101A',
          entity_type: 'Equipment',
          class_code: 'Equipment'
        },
        size: 10,
        x: 0,
        y: 0,
        color: '#000000',
        degree: 0
      }
    ]
    rawGraph.nodeIdMap = { 'P-101A': 0 }
    useGraphStore.setState({
      graphViewId: 'department-equipment',
      rawGraph
    })
    useSettingsStore.setState({ queryLabel: 'P-101A' })

    renderWithProviders(<GraphViewSelector />)
    fireEvent.click(screen.getByRole('button', { name: 'Fault causes' }))

    expect(useGraphStore.getState().graphViewId).toBe('department-equipment')
  })
})
