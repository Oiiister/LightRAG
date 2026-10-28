import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { getDocumentSourceFile, type DocStatusResponse } from '@/api/lightrag'
import FilePreviewDialog, {
  type PreviewFile
} from '@/components/ui/FilePreviewDialog'
import { errorMessage } from '@/lib/utils'

interface DocumentFilePreviewDialogProps {
  doc: DocStatusResponse
  open: boolean
  onOpenChange: (open: boolean) => void
}

type SourcePreviewState =
  | { status: 'loading' }
  | { status: 'ready'; file: PreviewFile }
  | { status: 'error'; message: string }

export default function DocumentFilePreviewDialog({
  doc,
  open,
  onOpenChange
}: DocumentFilePreviewDialogProps) {
  const { t } = useTranslation()
  const [state, setState] = useState<SourcePreviewState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    let previewUrl: string | null = null

    getDocumentSourceFile(doc.id, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return
        previewUrl = URL.createObjectURL(blob)
        setState({
          status: 'ready',
          file: {
            name: doc.file_path,
            type: blob.type,
            size: blob.size,
            preview: previewUrl,
            blob
          }
        })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setState({
          status: 'error',
          message: t('documentPanel.documentManager.preview.loadFailed', {
            error: errorMessage(error)
          })
        })
      })

    return () => {
      controller.abort()
      if (previewUrl !== null) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [doc.id, doc.file_path, t])

  return (
    <FilePreviewDialog
      file={state.status === 'ready' ? state.file : null}
      open={open}
      onOpenChange={onOpenChange}
      loading={state.status === 'loading'}
      errorMessage={state.status === 'error' ? state.message : null}
    />
  )
}
