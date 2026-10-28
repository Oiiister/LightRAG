import { describe, expect, mock, test } from 'bun:test'
import { act } from '@testing-library/react'

import { renderWithProviders } from '@/test/render'

mock.module('@react-sigma/graph-search', () => ({
  EdgeById: () => null
}))

const { default: GraphSearch } = await import('./GraphSearch')

describe('GraphSearch', () => {
  test('keeps the search surface width stable while hovered', async () => {
    const { getByLabelText } = renderWithProviders(
      <GraphSearch value={null} onChange={() => {}} />
    )
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0))
    })

    const input = getByLabelText('Search nodes in page...')
    const surface = input.closest('.rounded-xl')

    expect(surface).not.toBeNull()
    expect(surface?.className).toContain('w-[34rem]')
    expect(surface?.className).not.toContain('hover:w-fit')
    expect(surface?.className).not.toContain('transition-all')
  })
})
