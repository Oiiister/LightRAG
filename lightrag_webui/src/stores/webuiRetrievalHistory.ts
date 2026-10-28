import { createRetrievalHistoryStore } from './retrievalHistory'
import { WEBUI_RETRIEVAL_HISTORY_KEY } from '@/lib/storageKeys'
import { useWorkspaceStore } from './workspace'

/**
 * The admin entry's retrieval history is partitioned by the active storage
 * workspace. The default workspace keeps the original key so existing
 * deployments retain their history without migration.
 */
const stores = new Map<string, ReturnType<typeof createRetrievalHistoryStore>>()
const scopedKeyPrefix = `${WEBUI_RETRIEVAL_HISTORY_KEY}:`

function activeStorageKey(): string {
  const { activeWorkspaceId, defaultWorkspaceId } = useWorkspaceStore.getState()
  if (!activeWorkspaceId || activeWorkspaceId === defaultWorkspaceId) {
    return WEBUI_RETRIEVAL_HISTORY_KEY
  }
  return `${scopedKeyPrefix}${activeWorkspaceId}`
}

function activeStore() {
  const key = activeStorageKey()
  let store = stores.get(key)
  if (!store) {
    store = createRetrievalHistoryStore(key)
    stores.set(key, store)
  }
  return store
}

export const useWebuiRetrievalHistoryStore = {
  getState: () => activeStore().getState(),
  setState: (...args: Parameters<ReturnType<typeof activeStore>['setState']>) =>
    activeStore().setState(...args),
  subscribe: (...args: Parameters<ReturnType<typeof activeStore>['subscribe']>) =>
    activeStore().subscribe(...args)
}

/** Clear every workspace history, including persisted keys not yet mounted. */
export function clearAllWebuiRetrievalHistories(): void {
  for (const store of stores.values()) {
    store.getState().clearHistory()
  }
  stores.clear()
  try {
    const keys: string[] = []
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index)
      if (
        key === WEBUI_RETRIEVAL_HISTORY_KEY ||
        key?.startsWith(scopedKeyPrefix)
      ) {
        keys.push(key)
      }
    }
    for (const key of keys) localStorage.removeItem(key)
  } catch (error) {
    console.error('Failed to clear persisted admin retrieval histories:', error)
  }
}
