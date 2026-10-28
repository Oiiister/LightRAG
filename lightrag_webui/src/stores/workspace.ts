import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import { ACTIVE_WORKSPACE_STORAGE_KEY } from '@/lib/storageKeys'
import { createSelectors } from '@/lib/utils'

export type WorkspaceInfo = {
  id: string
  name: string
  is_default: boolean
  created_at: string
  updated_at: string
}

type WorkspaceState = {
  workspaces: WorkspaceInfo[]
  activeWorkspaceId: string | null
  defaultWorkspaceId: string | null
  setWorkspaceList: (workspaces: WorkspaceInfo[], defaultWorkspaceId: string) => void
  setActiveWorkspaceId: (workspaceId: string) => void
  upsertWorkspace: (workspace: WorkspaceInfo) => void
  removeWorkspace: (workspaceId: string) => void
  clearWorkspaces: () => void
}

const useWorkspaceStoreBase = create<WorkspaceState>()(
  persist(
    (set) => ({
      workspaces: [],
      activeWorkspaceId: null,
      defaultWorkspaceId: null,
      setWorkspaceList: (workspaces, defaultWorkspaceId) =>
        set((state) => {
          const activeStillExists = workspaces.some(
            (workspace) => workspace.id === state.activeWorkspaceId
          )
          return {
            workspaces,
            defaultWorkspaceId,
            activeWorkspaceId: activeStillExists ? state.activeWorkspaceId : defaultWorkspaceId
          }
        }),
      setActiveWorkspaceId: (activeWorkspaceId) => set({ activeWorkspaceId }),
      upsertWorkspace: (workspace) =>
        set((state) => {
          const existing = state.workspaces.some((item) => item.id === workspace.id)
          return {
            workspaces: existing
              ? state.workspaces.map((item) => (item.id === workspace.id ? workspace : item))
              : [...state.workspaces, workspace]
          }
        }),
      removeWorkspace: (workspaceId) =>
        set((state) => {
          const workspaces = state.workspaces.filter((workspace) => workspace.id !== workspaceId)
          return {
            workspaces,
            activeWorkspaceId:
              state.activeWorkspaceId === workspaceId
                ? state.defaultWorkspaceId
                : state.activeWorkspaceId
          }
        }),
      clearWorkspaces: () =>
        set({
          workspaces: [],
          activeWorkspaceId: null,
          defaultWorkspaceId: null
        })
    }),
    {
      name: ACTIVE_WORKSPACE_STORAGE_KEY,
      version: 1,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ activeWorkspaceId: state.activeWorkspaceId })
    }
  )
)

export const useWorkspaceStore = createSelectors(useWorkspaceStoreBase)

export const activeWorkspaceName = (): string => {
  const state = useWorkspaceStore.getState()
  return (
    state.workspaces.find((workspace) => workspace.id === state.activeWorkspaceId)?.name ??
    state.activeWorkspaceId ??
    ''
  )
}
