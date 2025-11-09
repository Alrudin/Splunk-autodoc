import { useState } from 'react'
import { api } from '@/lib/api'
import type { Upload } from '@/types'

interface UseUploadReturn {
  uploadFile: (projectId: number, file: File) => Promise<Upload | null>
  isUploading: boolean
  uploadProgress: number
  error: string | null
  reset: () => void
}

export function useUpload(): UseUploadReturn {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const uploadFile = async (projectId: number, file: File): Promise<Upload | null> => {
    try {
      setIsUploading(true)
      setUploadProgress(0)
      setError(null)

      const upload = await api.createUpload(projectId, file)
      
      if (upload) {
        setUploadProgress(100)
        setIsUploading(false)
        return upload
      }
      
      setIsUploading(false)
      return null
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload file'
      setError(errorMessage)
      setIsUploading(false)
      console.error('Failed to upload file:', err)
      return null
    }
  }

  const reset = () => {
    setIsUploading(false)
    setUploadProgress(0)
    setError(null)
  }

  return {
    uploadFile,
    isUploading,
    uploadProgress,
    error,
    reset,
  }
}
