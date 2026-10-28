import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { cleanup, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import * as api from '@/api/lightrag'
import { renderWithProviders } from '@/test/render'
import { useGraphStore } from '@/stores/graph'
import { useWorkspaceStore, type WorkspaceInfo } from '@/stores/workspace'
import WorkspaceSwitcher from './WorkspaceSwitcher'

const timestamp = '2026-01-01T00:00:00+00:00'

const defaultWorkspace: WorkspaceInfo = {
  id: 'default',
  name: 'Default',
  is_default: true,
  created_at: timestamp,
  updated_at: timestamp
}

const researchWorkspace: WorkspaceInfo = {
  id: 'ws_research',
  name: 'Research',
  is_default: false,
  created_at: timestamp,
  updated_at: timestamp
}

const requests: Array<{ method: string; url: string; workspace?: string; data?: any }> = []

const response = (config: any, data: any, status = 200) => ({
  data,
  status,
  statusText: 'OK',
  headers: { 'content-type': 'application/json' },
  config
})

beforeEach(() => {
  useWorkspaceStore.setState({
    workspaces: [defaultWorkspace, researchWorkspace],
    activeWorkspaceId: defaultWorkspace.id,
    defaultWorkspaceId: defaultWorkspace.id
  })
  useGraphStore.getState().reset()
  useGraphStore.setState({ selectedNode: 'old-workspace-node' })
  requests.length = 0

  api.__setAxiosAdapterForTests(async (config: any) => {
    const method = (config.method ?? 'get').toUpperCase()
    requests.push({
      method,
      url: config.url,
      workspace: config.headers?.['LIGHTRAG-WORKSPACE'],
      data: config.data ? JSON.parse(config.data) : undefined
    })

    if (method === 'GET' && config.url === '/workspaces') {
      return response(config, {
        workspaces: [defaultWorkspace, researchWorkspace],
        default_workspace_id: defaultWorkspace.id
      })
    }
    if (method === 'POST' && config.url === '/workspaces') {
      return response(
        config,
        {
          id: 'ws_legal',
          name: 'Legal',
          is_default: false,
          created_at: timestamp,
          updated_at: timestamp
        },
        201
      )
    }
    if (method === 'PATCH' && config.url === '/workspaces/ws_research') {
      return response(config, {
        ...researchWorkspace,
        name: 'Research Archive'
      })
    }
    if (method === 'DELETE' && config.url === '/workspaces/ws_research') {
      return response(config, { deleted: true, workspace: researchWorkspace })
    }
    return response(config, { response: 'ok' })
  })
})

afterEach(() => {
  cleanup()
  api.__setAxiosAdapterForTests(undefined)
  useGraphStore.getState().reset()
  localStorage.clear()
})

describe('WorkspaceSwitcher', () => {
  test('lists workspaces and switches the request scope', async () => {
    const user = userEvent.setup()
    renderWithProviders(<WorkspaceSwitcher />)

    await user.click(screen.getByRole('button', { name: /switch workspace/i }))
    const dialog = await screen.findByRole('dialog')
    await waitFor(() =>
      expect(
        requests.find(
          (request) => request.method === 'GET' && request.url === '/workspaces'
        )?.workspace
      ).toBe('')
    )
    await user.click(within(dialog).getByRole('button', { name: /open workspace research/i }))

    await waitFor(() =>
      expect(useWorkspaceStore.getState().activeWorkspaceId).toBe(researchWorkspace.id)
    )
    expect(useGraphStore.getState().selectedNode).toBeNull()

    await api.queryText({
      query: 'test',
      mode: 'mix',
      stream: false
    })
    const queryRequest = requests.find(
      (request) => request.method === 'POST' && request.url === '/query'
    )
    expect(queryRequest?.workspace).toBe(researchWorkspace.id)

    await api.verifyCredentials()
    const authRequest = requests.find((request) => request.url === '/auth/verify')
    expect(authRequest?.workspace).toBeUndefined()
  })

  test('creates a workspace and makes it active', async () => {
    const user = userEvent.setup()
    renderWithProviders(<WorkspaceSwitcher />)

    await user.click(screen.getByRole('button', { name: /switch workspace/i }))
    await user.type(await screen.findByPlaceholderText(/new workspace name/i), 'Legal')
    await user.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => expect(useWorkspaceStore.getState().activeWorkspaceId).toBe('ws_legal'))
    expect(
      useWorkspaceStore.getState().workspaces.some((workspace) => workspace.id === 'ws_legal')
    ).toBe(true)
  })

  test('renames and deletes non-default workspaces', async () => {
    const user = userEvent.setup()
    renderWithProviders(<WorkspaceSwitcher />)

    await user.click(screen.getByRole('button', { name: /switch workspace/i }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getAllByRole('button', { name: 'Rename' })[1])
    const nameInput = within(dialog).getByRole('textbox', { name: 'Workspace name' })
    await user.clear(nameInput)
    await user.type(nameInput, 'Research Archive')
    await user.click(within(dialog).getByRole('button', { name: 'Save' }))

    await waitFor(() =>
      expect(
        useWorkspaceStore
          .getState()
          .workspaces.find((workspace) => workspace.id === researchWorkspace.id)?.name
      ).toBe('Research Archive')
    )

    await user.click(within(dialog).getAllByRole('button', { name: 'Delete' })[1])
    const alert = await screen.findByRole('alertdialog')
    await user.click(within(alert).getByRole('button', { name: /delete workspace/i }))

    await waitFor(() =>
      expect(
        useWorkspaceStore
          .getState()
          .workspaces.some((workspace) => workspace.id === researchWorkspace.id)
      ).toBe(false)
    )
  })
})
