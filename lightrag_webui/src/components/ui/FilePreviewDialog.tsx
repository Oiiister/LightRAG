import * as React from 'react'
import { FileText } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/Dialog'
import {
  formatFileSize,
  getFilePreviewKind,
  MAX_TEXT_PREVIEW_BYTES
} from '@/lib/filePreview'

export interface PreviewFile {
  name: string
  type: string
  size: number
  preview: string
  blob: Blob
}

interface FilePreviewDialogProps {
  file: PreviewFile | null
  open: boolean
  onOpenChange: (open: boolean) => void
  loading?: boolean
  errorMessage?: string | null
}

type TextPreviewState =
  | { status: 'loading' }
  | { status: 'ready'; content: string }
  | { status: 'error' }

function TextFilePreview({ file }: { file: PreviewFile }) {
  const { t } = useTranslation()
  const [state, setState] = React.useState<TextPreviewState>({ status: 'loading' })

  React.useEffect(() => {
    let cancelled = false

    file.blob
      .slice(0, MAX_TEXT_PREVIEW_BYTES)
      .text()
      .then((content) => {
        if (!cancelled) {
          setState({ status: 'ready', content })
        }
      })
      .catch(() => {
        if (!cancelled) {
          setState({ status: 'error' })
        }
      })

    return () => {
      cancelled = true
    }
  }, [file.blob])

  if (state.status === 'loading') {
    return (
      <p className="text-muted-foreground p-6 text-sm">
        {t('documentPanel.uploadDocuments.fileUploader.previewLoading')}
      </p>
    )
  }

  if (state.status === 'error') {
    return (
      <p className="text-destructive p-6 text-sm">
        {t('documentPanel.uploadDocuments.fileUploader.previewError')}
      </p>
    )
  }

  return (
    <div className="space-y-3 p-4">
      {file.size > MAX_TEXT_PREVIEW_BYTES ? (
        <p className="text-muted-foreground text-xs">
          {t('documentPanel.uploadDocuments.fileUploader.previewTruncated', {
            maxSize: formatFileSize(MAX_TEXT_PREVIEW_BYTES)
          })}
        </p>
      ) : null}
      <pre className="whitespace-pre-wrap break-words font-mono text-sm">
        {state.content ||
          t('documentPanel.uploadDocuments.fileUploader.previewEmptyFile')}
      </pre>
    </div>
  )
}

export default function FilePreviewDialog({
  file,
  open,
  onOpenChange,
  loading = false,
  errorMessage = null
}: FilePreviewDialogProps) {
  const { t } = useTranslation()
  if (!file && !loading && !errorMessage) return null

  const previewKind = file ? getFilePreviewKind(file) : null
  const description = file
    ? t('documentPanel.uploadDocuments.fileUploader.previewDescription', {
      size: formatFileSize(file.size)
    })
    : loading
      ? t('documentPanel.uploadDocuments.fileUploader.previewLoading')
      : errorMessage

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-hidden sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle className="break-all pr-8">
            {file?.name ??
              t('documentPanel.uploadDocuments.fileUploader.previewFile')}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="min-h-72 overflow-auto rounded-md border bg-muted/30">
          {loading ? (
            <p className="text-muted-foreground p-6 text-sm">
              {t('documentPanel.uploadDocuments.fileUploader.previewLoading')}
            </p>
          ) : errorMessage ? (
            <p className="text-destructive p-6 text-sm">{errorMessage}</p>
          ) : file && previewKind === 'image' ? (
            <div className="flex min-h-72 items-center justify-center p-4">
              <img
                src={file.preview}
                alt={t('documentPanel.uploadDocuments.fileUploader.previewImageAlt', {
                  name: file.name
                })}
                className="max-h-[70vh] max-w-full object-contain"
              />
            </div>
          ) : file && previewKind === 'pdf' ? (
            <object
              data={file.preview}
              type="application/pdf"
              title={t('documentPanel.uploadDocuments.fileUploader.previewPdfTitle', {
                name: file.name
              })}
              className="h-[70vh] w-full bg-white"
            >
              <p className="text-muted-foreground p-6 text-sm">
                {t('documentPanel.uploadDocuments.fileUploader.previewUnavailableDescription')}
              </p>
            </object>
          ) : file && previewKind === 'text' ? (
            <TextFilePreview file={file} />
          ) : file ? (
            <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center">
              <FileText className="text-muted-foreground size-12" aria-hidden="true" />
              <div className="space-y-1">
                <p className="font-medium">
                  {t('documentPanel.uploadDocuments.fileUploader.previewUnavailableTitle')}
                </p>
                <p className="text-muted-foreground max-w-md text-sm">
                  {t('documentPanel.uploadDocuments.fileUploader.previewUnavailableDescription')}
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}
