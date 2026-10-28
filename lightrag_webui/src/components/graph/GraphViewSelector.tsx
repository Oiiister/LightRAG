import { useTranslation } from 'react-i18next'
import { FileStack, Factory, Network, GitBranch } from 'lucide-react'
import { toast } from 'sonner'

import type { GraphViewId } from '@/api/lightrag'
import { useGraphStore } from '@/stores/graph'
import { useSettingsStore } from '@/stores/settings'
import { FAULT_DEPTH_STYLES } from '@/utils/faultDepthStyle'
import { isFaultEventType, resolveNodeType } from '@/utils/nodeType'

const VIEWS: Array<{
  id: GraphViewId
  labelKey: string
  fallback: string
  icon: typeof FileStack
}> = [
  {
    id: 'department-files',
    labelKey: 'graphPanel.graphViews.departmentFiles',
    fallback: '部门文件',
    icon: FileStack
  },
  {
    id: 'department-equipment',
    labelKey: 'graphPanel.graphViews.departmentEquipment',
    fallback: '部门设备',
    icon: Factory
  },
  {
    id: 'equipment-faults',
    labelKey: 'graphPanel.graphViews.equipmentFaults',
    fallback: '设备故障',
    icon: Network
  },
  {
    id: 'fault-causes',
    labelKey: 'graphPanel.graphViews.faultCauses',
    fallback: '故障因果',
    icon: GitBranch
  }
]

const GraphViewSelector = () => {
  const { t } = useTranslation()
  const graphViewId = useGraphStore.use.graphViewId()
  const queryLabel = useSettingsStore.use.queryLabel()
  const needsRoot = graphViewId === 'fault-causes'
  const missingRoot = needsRoot && (!queryLabel || queryLabel === '*')

  const selectView = (viewId: GraphViewId) => {
    if (viewId === graphViewId) return
    const state = useGraphStore.getState()
    if (viewId === 'fault-causes' && queryLabel && queryLabel !== '*') {
      const rootNode = state.rawGraph?.nodes.find(
        (node) =>
          node.id === queryLabel ||
          node.properties?.entity_id === queryLabel
      )
      if (rootNode) {
        const rootType = resolveNodeType(rootNode.properties)
        if (!isFaultEventType(rootType)) {
          toast.error(
            t('graphPanel.graphViews.invalidFaultRoot', {
              root: queryLabel,
              type: rootType
            })
          )
          return
        }
      }
    }
    state.setGraphViewId(viewId)
    state.setGraphDataFetchAttempted(false)
    state.setLastSuccessfulQueryLabel('')
    state.clearSelection()
    state.incrementGraphDataVersion()
  }

  return (
    <div className="bg-background/85 flex flex-col items-center gap-1 rounded-xl border-2 px-2 py-1.5 shadow-sm backdrop-blur-lg">
      <div className="flex items-center gap-1">
        {VIEWS.map(({ id, labelKey, fallback, icon: Icon }) => {
          const active = id === graphViewId
          return (
            <button
              key={id}
              type="button"
              className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors ${
                active
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-primary/10'
              }`}
              aria-pressed={active}
              onClick={() => selectView(id)}
            >
              <Icon className="size-3.5" aria-hidden="true" />
              <span>{t(labelKey, fallback)}</span>
            </button>
          )
        })}
      </div>
      {missingRoot && (
        <span className="text-muted-foreground text-[11px]">
          {t(
            'graphPanel.graphViews.selectFaultHint',
            '请在上方标签搜索中选择一个故障事件作为因果图根节点'
          )}
        </span>
      )}
      {!missingRoot && graphViewId === 'fault-causes' && (
        <div className="flex items-center gap-2">
          {FAULT_DEPTH_STYLES.map(({ band, color, size }) => (
            <span
              key={band}
              className="text-muted-foreground flex items-center gap-1 text-[10px]"
            >
              <span
                className="inline-block rounded-full"
                style={{
                  backgroundColor: color,
                  width: Math.max(6, size / 2),
                  height: Math.max(6, size / 2)
                }}
              />
              {band === 0
                ? t('graphPanel.faultDepth.root', '根故障')
                : band === FAULT_DEPTH_STYLES.length - 1
                  ? t('graphPanel.faultDepth.deeper', '{{band}}+级原因', {
                    band
                  })
                  : t('graphPanel.faultDepth.level', '{{band}}级原因', {
                    band
                  })}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default GraphViewSelector
