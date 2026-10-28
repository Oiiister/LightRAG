import { afterEach, beforeEach, describe, expect, mock, spyOn, test } from 'bun:test'
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'

import FileUploader from '@/components/ui/FileUploader'
import { renderWithProviders } from '@/test/render'

const acceptedExtensions = ['.docx', '.pdf', '.png', '.txt']
const onUpload = mock(async () => {})

let nextPreviewUrl = 1
let createObjectURLSpy: ReturnType<typeof spyOn>
let revokeObjectURLSpy: ReturnType<typeof spyOn>

beforeEach(() => {
  nextPreviewUrl = 1
  createObjectURLSpy = spyOn(URL, 'createObjectURL').mockImplementation(
    () => `blob:preview-${nextPreviewUrl++}`
  )
  revokeObjectURLSpy = spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
})

afterEach(() => {
  cleanup()
  createObjectURLSpy.mockRestore()
  revokeObjectURLSpy.mockRestore()
  onUpload.mockClear()
})

function renderUploader() {
  const result = renderWithProviders(
    <FileUploader
      maxFileCount={1}
      acceptedExtensions={acceptedExtensions}
      onUpload={onUpload}
    />
  )
  const input = result.container.querySelector<HTMLInputElement>('input[type="file"]')
  expect(Boolean(input)).toBe(true)
  return { ...result, input: input! }
}

async function chooseFile(file: File) {
  const result = renderUploader()
  fireEvent.change(result.input, { target: { files: [file] } })

  await screen.findByText(file.name)
  await waitFor(() => expect(onUpload).toHaveBeenCalledTimes(1))
  return result
}

describe('FileUploader preview', () => {
  test('shows an image preview without delaying the upload', async () => {
    const file = new File(['image bytes'], 'diagram.png', { type: 'image/png' })
    await chooseFile(file)

    fireEvent.click(screen.getByRole('button', { name: 'Preview file' }))

    const image = await screen.findByRole('img', { name: 'Preview of diagram.png' })
    expect(image.getAttribute('src')).toBe('blob:preview-1')
    expect(onUpload).toHaveBeenCalledTimes(1)
  })

  test('renders text file contents as escaped preview text', async () => {
    const file = new File(['Pump P-101A: bearing temperature high'], 'notes.txt', {
      type: 'text/plain'
    })
    await chooseFile(file)

    fireEvent.click(screen.getByRole('button', { name: 'Preview file' }))

    expect(
      (await screen.findByText('Pump P-101A: bearing temperature high')).textContent
    ).toBe('Pump P-101A: bearing temperature high')
  })

  test('uses the browser PDF viewer for PDF files', async () => {
    const file = new File(['%PDF-1.7'], 'manual.pdf', { type: 'application/pdf' })
    await chooseFile(file)

    fireEvent.click(screen.getByRole('button', { name: 'Preview file' }))

    const pdf = await screen.findByTitle('PDF preview for manual.pdf')
    expect(pdf.getAttribute('data')).toBe('blob:preview-1')
  })

  test('explains when a browser cannot render the file type', async () => {
    const file = new File(['document bytes'], 'manual.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    })
    await chooseFile(file)

    fireEvent.click(screen.getByRole('button', { name: 'Preview file' }))

    expect(
      (await screen.findByText('Preview not available')).textContent
    ).toBe('Preview not available')
    expect(
      screen.getByText(
        'This file type cannot be previewed in the browser. You can still upload it.'
      ).textContent
    ).toContain('still upload it')
  })
})
