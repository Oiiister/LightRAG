import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckIcon, FoldersIcon, PencilIcon, PlusIcon, SearchIcon, Trash2Icon } from 'lucide-react'
import { toast } from 'sonner'

import { createWorkspace, deleteWorkspace, getWorkspaces, renameWorkspace } from '@/api/lightrag'
import Button from '@/components/ui/Button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/Dialog'
import Input from '@/components/ui/Input'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/AlertDialog'
import { errorMessage } from '@/lib/utils'
import { useGraphStore } from '@/stores/graph'
import { useSettingsStore } from '@/stores/settings'
import { useWorkspaceStore, type WorkspaceInfo } from '@/stores/workspace'

function clearGraphForWorkspaceSwitch(): void {
  const graphStore = useGraphStore.getState()
  const sigma = graphStore.sigmaInstance
  graphStore.reset()
  graphStore.setGraphDataFetchAttempted(false)
  graphStore.setLabelsFetchAttempted(false)
  graphStore.setSigmaInstance(null)
  graphStore.setIsFetching(false)
  if (sigma) {
    sigma.getGraph().clear()
    sigma.kill()
  }
}

export default function WorkspaceSwitcher() {
  const { t } = useTranslation()
  const workspaces = useWorkspaceStore.use.workspaces()
  const activeWorkspaceId = useWorkspaceStore.use.activeWorkspaceId()
  const setWorkspaceList = useWorkspaceStore.use.setWorkspaceList()
  const setActiveWorkspaceId = useWorkspaceStore.use.setActiveWorkspaceId()
  const upsertWorkspace = useWorkspaceStore.use.upsertWorkspace()
  const removeWorkspace = useWorkspaceStore.use.removeWorkspace()

  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')
  const [renaming, setRenaming] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<WorkspaceInfo | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadWorkspaces = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getWorkspaces()
      setWorkspaceList(response.workspaces, response.default_workspace_id)
    } catch (error) {
      toast.error(
        t('workspaceSwitcher.loadFailed', {
          error: errorMessage(error),
          defaultValue: 'Could not load workspaces: {{error}}'
        })
      )
    } finally {
      setLoading(false)
    }
  }, [setWorkspaceList, t])

  useEffect(() => {
    if (!open) return
    const timer = setTimeout(() => void loadWorkspaces(), 0)
    return () => clearTimeout(timer)
  }, [open, loadWorkspaces])

  const activeWorkspace = workspaces.find((workspace) => workspace.id === activeWorkspaceId)
  const displayName = (workspace: WorkspaceInfo) =>
    workspace.is_default && workspace.name === 'Default'
      ? t('workspaceSwitcher.defaultName', 'Default workspace')
      : workspace.name
  const normalizedQuery = query.trim().toLocaleLowerCase()
  const filteredWorkspaces = workspaces.filter((workspace) => {
    if (!normalizedQuery) return true
    return (
      workspace.name.toLocaleLowerCase().includes(normalizedQuery) ||
      workspace.id.toLocaleLowerCase().includes(normalizedQuery)
    )
  })

  const handleSwitch = (workspace: WorkspaceInfo) => {
    useSettingsStore.getState().setQueryLabel('')
    clearGraphForWorkspaceSwitch()
    setActiveWorkspaceId(workspace.id)
    setOpen(false)
  }

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name || creating) return
    setCreating(true)
    try {
      const workspace = await createWorkspace(name)
      upsertWorkspace(workspace)
      useSettingsStore.getState().setQueryLabel('')
      clearGraphForWorkspaceSwitch()
      setActiveWorkspaceId(workspace.id)
      setNewName('')
      setOpen(false)
      toast.success(
        t('workspaceSwitcher.created', {
          name: workspace.name,
          defaultValue: 'Created workspace "{{name}}"'
        })
      )
    } catch (error) {
      toast.error(
        t('workspaceSwitcher.createFailed', {
          error: errorMessage(error),
          defaultValue: 'Could not create workspace: {{error}}'
        })
      )
    } finally {
      setCreating(false)
    }
  }

  const startRename = (workspace: WorkspaceInfo) => {
    setEditingId(workspace.id)
    setEditingName(workspace.name)
  }

  const handleRename = async () => {
    const name = editingName.trim()
    if (!editingId || !name || renaming) return
    setRenaming(true)
    try {
      const workspace = await renameWorkspace(editingId, name)
      upsertWorkspace(workspace)
      setEditingId(null)
      toast.success(
        t('workspaceSwitcher.renamed', {
          name: workspace.name,
          defaultValue: 'Renamed workspace to "{{name}}"'
        })
      )
    } catch (error) {
      toast.error(
        t('workspaceSwitcher.renameFailed', {
          error: errorMessage(error),
          defaultValue: 'Could not rename workspace: {{error}}'
        })
      )
    } finally {
      setRenaming(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget || deleting) return
    setDeleting(true)
    try {
      await deleteWorkspace(deleteTarget.id)
      if (deleteTarget.id === activeWorkspaceId) {
        useSettingsStore.getState().setQueryLabel('')
        clearGraphForWorkspaceSwitch()
      }
      removeWorkspace(deleteTarget.id)
      toast.success(
        t('workspaceSwitcher.deleted', {
          name: deleteTarget.name,
          defaultValue: 'Deleted workspace "{{name}}"'
        })
      )
      setDeleteTarget(null)
    } catch (error) {
      toast.error(
        t('workspaceSwitcher.deleteFailed', {
          error: errorMessage(error),
          defaultValue: 'Could not delete workspace: {{error}}'
        })
      )
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="max-w-12 gap-1.5 sm:max-w-52"
        onClick={() => setOpen(true)}
        aria-label={t('workspaceSwitcher.switchButton', 'Switch workspace')}
      >
        <FoldersIcon className="size-4 shrink-0" aria-hidden="true" />
        <span className="hidden truncate sm:inline">
          {activeWorkspace
            ? displayName(activeWorkspace)
            : t('workspaceSwitcher.loadingWorkspace', 'Workspace')}
        </span>
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-hidden sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('workspaceSwitcher.title', 'Workspaces')}</DialogTitle>
            <DialogDescription>
              {t(
                'workspaceSwitcher.description',
                'Documents, knowledge graphs and retrieval are isolated by workspace.'
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="relative">
            <SearchIcon
              className="text-muted-foreground pointer-events-none absolute top-2.5 left-3 size-4"
              aria-hidden="true"
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="pl-9"
              placeholder={t('workspaceSwitcher.searchPlaceholder', 'Search workspaces')}
              aria-label={t('workspaceSwitcher.searchPlaceholder', 'Search workspaces')}
            />
          </div>

          <div className="max-h-[45vh] min-h-32 space-y-2 overflow-y-auto pr-1">
            {filteredWorkspaces.map((workspace) => {
              const isActive = workspace.id === activeWorkspaceId
              const isEditing = editingId === workspace.id
              return (
                <div
                  key={workspace.id}
                  className="border-border/70 flex items-center gap-2 rounded-md border p-2"
                >
                  {isEditing ? (
                    <>
                      <Input
                        autoFocus
                        value={editingName}
                        maxLength={80}
                        onChange={(event) => setEditingName(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') void handleRename()
                          if (event.key === 'Escape') setEditingId(null)
                        }}
                        aria-label={t('workspaceSwitcher.newName', 'Workspace name')}
                      />
                      <Button
                        size="sm"
                        onClick={() => void handleRename()}
                        disabled={!editingName.trim() || renaming}
                      >
                        {t('workspaceSwitcher.save', 'Save')}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                        {t('workspaceSwitcher.cancel', 'Cancel')}
                      </Button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="hover:bg-accent flex min-w-0 flex-1 items-center gap-2 rounded-sm px-1 py-0.5 text-left"
                        onClick={() => handleSwitch(workspace)}
                        aria-label={t('workspaceSwitcher.openWorkspace', {
                          name: displayName(workspace),
                          defaultValue: 'Open workspace {{name}}'
                        })}
                      >
                        <span className="flex size-5 shrink-0 items-center justify-center">
                          {isActive && (
                            <CheckIcon className="size-4 text-emerald-500" aria-hidden="true" />
                          )}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate font-medium">
                            {displayName(workspace)}
                          </span>
                          <span className="text-muted-foreground block truncate text-xs">
                            {workspace.id}
                          </span>
                        </span>
                        {workspace.is_default && (
                          <span className="bg-muted ml-auto rounded px-1.5 py-0.5 text-xs">
                            {t('workspaceSwitcher.default', 'Default')}
                          </span>
                        )}
                      </button>
                      <Button
                        variant="ghost"
                        size="icon"
                        tooltip={t('workspaceSwitcher.rename', 'Rename')}
                        aria-label={t('workspaceSwitcher.rename', 'Rename')}
                        onClick={() => startRename(workspace)}
                      >
                        <PencilIcon aria-hidden="true" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        tooltip={t('workspaceSwitcher.delete', 'Delete')}
                        aria-label={t('workspaceSwitcher.delete', 'Delete')}
                        disabled={workspace.is_default}
                        onClick={() => setDeleteTarget(workspace)}
                      >
                        <Trash2Icon aria-hidden="true" />
                      </Button>
                    </>
                  )}
                </div>
              )
            })}
            {!loading && filteredWorkspaces.length === 0 && (
              <p className="text-muted-foreground py-6 text-center text-sm">
                {query
                  ? t('workspaceSwitcher.noMatches', 'No matching workspaces')
                  : t('workspaceSwitcher.empty', 'No workspaces yet')}
              </p>
            )}
          </div>

          <DialogFooter className="border-t pt-4">
            <div className="flex w-full gap-2">
              <Input
                value={newName}
                maxLength={80}
                placeholder={t('workspaceSwitcher.createPlaceholder', 'New workspace name')}
                aria-label={t('workspaceSwitcher.createPlaceholder', 'New workspace name')}
                onChange={(event) => setNewName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') void handleCreate()
                }}
              />
              <Button onClick={() => void handleCreate()} disabled={!newName.trim() || creating}>
                <PlusIcon aria-hidden="true" />
                {t('workspaceSwitcher.create', 'Create')}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={deleteTarget !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen && !deleting) setDeleteTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('workspaceSwitcher.deleteTitle', 'Delete workspace?')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('workspaceSwitcher.deleteDescription', {
                name: deleteTarget?.name ?? '',
                defaultValue:
                  'This permanently deletes every document, graph, vector and query index in "{{name}}". This cannot be undone.'
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>
              {t('workspaceSwitcher.cancel', 'Cancel')}
            </AlertDialogCancel>
            <AlertDialogAction asChild>
              <Button
                variant="destructive"
                disabled={deleting}
                onClick={(event) => {
                  event.preventDefault()
                  void handleDelete()
                }}
              >
                {t('workspaceSwitcher.deleteConfirm', 'Delete workspace')}
              </Button>
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
