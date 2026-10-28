import { extractFileExtension } from '@/lib/fileTypes'

export const MAX_TEXT_PREVIEW_BYTES = 512 * 1024

const IMAGE_FILE_EXTENSIONS = new Set([
  '.avif',
  '.bmp',
  '.gif',
  '.jpeg',
  '.jpg',
  '.png',
  '.svg',
  '.webp'
])

const TEXT_FILE_EXTENSIONS = new Set([
  '.bat',
  '.c',
  '.conf',
  '.cpp',
  '.css',
  '.csv',
  '.go',
  '.h',
  '.hpp',
  '.htm',
  '.html',
  '.ini',
  '.java',
  '.js',
  '.json',
  '.less',
  '.log',
  '.md',
  '.mdx',
  '.php',
  '.properties',
  '.py',
  '.rb',
  '.rtf',
  '.scss',
  '.sh',
  '.sql',
  '.swift',
  '.tex',
  '.ts',
  '.txt',
  '.xml',
  '.yaml',
  '.yml'
])

const TEXT_APPLICATION_TYPES = new Set([
  'application/javascript',
  'application/json',
  'application/sql',
  'application/xml',
  'application/x-httpd-php',
  'application/x-sh',
  'application/x-yaml',
  'application/yaml'
])

export type FilePreviewKind = 'image' | 'pdf' | 'text' | 'unsupported'

export function getFilePreviewKind(
  file: Pick<File, 'name' | 'type'>
): FilePreviewKind {
  const extension = extractFileExtension(file.name)
  const mimeType = file.type.toLowerCase()

  if (mimeType.startsWith('image/') || IMAGE_FILE_EXTENSIONS.has(extension)) {
    return 'image'
  }
  if (mimeType === 'application/pdf' || extension === '.pdf') {
    return 'pdf'
  }
  if (
    mimeType.startsWith('text/') ||
    TEXT_APPLICATION_TYPES.has(mimeType) ||
    TEXT_FILE_EXTENSIONS.has(extension)
  ) {
    return 'text'
  }
  return 'unsupported'
}

export function formatFileSize(
  bytes: number,
  opts: {
    decimals?: number
    sizeType?: 'accurate' | 'normal'
  } = {}
): string {
  const { decimals = 0, sizeType = 'normal' } = opts

  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const accurateSizes = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB']
  if (bytes === 0) return '0 Byte'
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(decimals)} ${
    sizeType === 'accurate' ? (accurateSizes[i] ?? 'Bytes') : (sizes[i] ?? 'Bytes')
  }`
}
