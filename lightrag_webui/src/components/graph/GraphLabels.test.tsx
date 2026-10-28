import { beforeEach, describe, expect, mock, test } from 'bun:test'
import { fireEvent, screen, waitFor } from '@testing-library/react'

import * as realApi from '@/api/lightrag'
import { SearchHistoryManager } from '@/utils/SearchHistoryManager'
import { useSettingsStore } from '@/stores/settings'
import { renderWithProviders } from '@/test/render'

const gateId = 'GATE-OR-9333dd5903b9cf4a'
const typedLabels = [
  { label: '浮点例外', type: 'FaultEvent', exists: true },
  { label: '螺杆空压机', type: 'Equipment', exists: true },
  { label: gateId, type: 'LogicGate', exists: true }
]

const getPopularLabelOptions = mock(async () => typedLabels)
const searchLabelOptions = mock(async () => typedLabels)
const resolveDetails = (labels: string[]): realApi.GraphLabelOption[] =>
  labels.map((label) =>
    typedLabels.find((option) => option.label === label) ?? {
      label,
      type: '',
      exists: false
    }
  )
const getLabelDetails = mock(
  async (labels: string[]): Promise<realApi.GraphLabelOption[]> =>
    resolveDetails(labels)
)

mock.module('@/api/lightrag', () => ({
  ...realApi,
  getPopularLabelOptions,
  searchLabelOptions,
  getLabelDetails
}))

const { default: GraphLabels } = await import('./GraphLabels')

describe('GraphLabels', () => {
  beforeEach(() => {
    localStorage.clear()
    useSettingsStore.setState({ queryLabel: '*' })
    getPopularLabelOptions.mockClear()
    searchLabelOptions.mockClear()
    getLabelDetails.mockClear()
    getLabelDetails.mockImplementation(async (labels) => resolveDetails(labels))
  })

  test('shows each label type in the node selector', async () => {
    SearchHistoryManager.mergePopularLabels(
      typedLabels.map((option) => option.label)
    )
    renderWithProviders(<GraphLabels />)

    await waitFor(() => {
      expect(getPopularLabelOptions).toHaveBeenCalled()
    })
    fireEvent.click(
      screen.getByRole('combobox', { name: 'Search node name' })
    )

    expect((await screen.findAllByText('FaultEvent')).length).toBe(1)
    expect(screen.getAllByText('Equipment').length).toBe(1)
  })

  test('hides gate hashes while selecting the stable gate id', async () => {
    SearchHistoryManager.mergePopularLabels(
      typedLabels.map((option) => option.label)
    )
    renderWithProviders(<GraphLabels />)

    await waitFor(() => {
      expect(getPopularLabelOptions).toHaveBeenCalled()
    })
    fireEvent.click(
      screen.getByRole('combobox', { name: 'Search node name' })
    )

    expect(screen.queryAllByText(gateId)).toHaveLength(0)
    fireEvent.click(await screen.findByText('GATE-OR'))

    await waitFor(() => {
      expect(useSettingsStore.getState().queryLabel).toBe(gateId)
    })
  })

  test('hides history labels the backend confirms no longer exist', async () => {
    SearchHistoryManager.addToHistory('冷却能力不足')
    getLabelDetails.mockImplementation(async (labels) =>
      labels.map((label) => ({
        label,
        type: 'Unknown',
        exists: false
      }))
    )

    renderWithProviders(<GraphLabels />)
    await waitFor(() => {
      expect(getPopularLabelOptions).toHaveBeenCalled()
    })
    fireEvent.click(
      screen.getByRole('combobox', { name: 'Search node name' })
    )

    await waitFor(() => {
      expect(getLabelDetails).toHaveBeenCalled()
      expect(screen.queryAllByText('冷却能力不足')).toHaveLength(0)
    })
  })
})
