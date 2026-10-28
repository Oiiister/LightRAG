import { afterEach, describe, expect, test } from 'bun:test'

import {
  clearAllWebuiRetrievalHistories,
  useWebuiRetrievalHistoryStore
} from './webuiRetrievalHistory'
import { useWorkspaceStore } from './workspace'

const message = (id: string, content: string) => ({
  id,
  role: 'user' as const,
  content
})

afterEach(() => {
  clearAllWebuiRetrievalHistories()
  useWorkspaceStore.setState({
    workspaces: [],
    activeWorkspaceId: null,
    defaultWorkspaceId: null
  })
  localStorage.clear()
})

describe('workspace-scoped admin retrieval history', () => {
  test('keeps each workspace conversation separate and restores it on return', () => {
    useWorkspaceStore.setState({
      workspaces: [
        {
          id: 'default',
          name: 'Default',
          is_default: true,
          created_at: '',
          updated_at: ''
        },
        {
          id: 'ws_research',
          name: 'Research',
          is_default: false,
          created_at: '',
          updated_at: ''
        }
      ],
      activeWorkspaceId: 'default',
      defaultWorkspaceId: 'default'
    })

    useWebuiRetrievalHistoryStore
      .getState()
      .setHistory([message('d1', 'default question')])

    useWorkspaceStore.getState().setActiveWorkspaceId('ws_research')
    expect(useWebuiRetrievalHistoryStore.getState().history).toEqual([])
    useWebuiRetrievalHistoryStore
      .getState()
      .setHistory([message('r1', 'research question')])

    useWorkspaceStore.getState().setActiveWorkspaceId('default')
    expect(useWebuiRetrievalHistoryStore.getState().history).toEqual([
      message('d1', 'default question')
    ])

    useWorkspaceStore.getState().setActiveWorkspaceId('ws_research')
    expect(useWebuiRetrievalHistoryStore.getState().history).toEqual([
      message('r1', 'research question')
    ])
  })
})
