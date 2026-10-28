import type { GraphViewId } from '@/api/lightrag'

export const resolveGraphViewRoot = (
  viewId: GraphViewId,
  label: string
): string | null => {
  if (
    viewId === 'department-files' ||
    viewId === 'department-equipment'
  ) {
    return null
  }
  return label && label !== '*' ? label : null
}

export const canLoadGraphView = (
  viewId: GraphViewId,
  label: string
): boolean =>
  viewId !== 'fault-causes' || resolveGraphViewRoot(viewId, label) !== null

export const isInvalidFaultRootResponse = (
  status: number | undefined,
  message: string
): boolean =>
  status === 400 &&
  message.includes('fault-causes root must be a FaultEvent')

export const isMissingFaultRootResponse = (
  status: number | undefined,
  message: string
): boolean =>
  status === 404 &&
  message.includes('graph view root') &&
  message.includes('was not found')
