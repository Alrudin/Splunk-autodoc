import { useState, useRef, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useUpload } from '@/hooks/useUpload'
import { useJobPolling } from '@/hooks/useJobPolling'
import { useStore } from '@/store'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useToast } from '@/hooks/use-toast'
import {
  Upload as UploadIcon,
  FileArchive,
  CheckCircle,
  XCircle,
  Loader2,
  ExternalLink,
  X,
} from 'lucide-react'
import type { Upload, Job } from '@/types'

export function UploadPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { currentProject } = useStore()
  const { uploadFile, isUploading, uploadProgress, error: uploadError } = useUpload()
  const { job, isPolling, startPolling, reset: resetJobPolling } = useJobPolling()

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [uploadResult, setUploadResult] = useState<Upload | null>(null)
  const [isCreatingJob, setIsCreatingJob] = useState(false)
  const [showLogsDialog, setShowLogsDialog] = useState(false)
  const [graphId, setGraphId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): boolean => {
    const validExtensions = ['.zip', '.tar.gz', '.tar', '.tgz']
    const isValid = validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext))

    if (!isValid) {
      toast({
        title: 'Invalid file type',
        description: 'Please upload a .zip, .tar.gz, .tar, or .tgz file',
        variant: 'destructive',
      })
      return false
    }

    const maxSize = 2 * 1024 * 1024 * 1024 // 2GB
    if (file.size > maxSize) {
      toast({
        title: 'File too large',
        description: 'Maximum file size is 2GB',
        variant: 'destructive',
      })
      return false
    }

    return true
  }

  const handleFileSelect = (file: File) => {
    if (validateFile(file)) {
      setSelectedFile(file)
      setUploadResult(null)
    }
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(true)
  }

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  const handleUpload = async () => {
    if (!selectedFile || !currentProject) return

    try {
      // Upload file
      const upload = await uploadFile(currentProject.id, selectedFile)
      if (!upload) {
        toast({
          title: 'Upload failed',
          description: uploadError || 'Failed to upload file',
          variant: 'destructive',
        })
        return
      }

      setUploadResult(upload)
      toast({
        title: 'File uploaded',
        description: 'Creating processing job...',
      })

      // Create job
      setIsCreatingJob(true)
      const newJob = await api.createJob(upload.id)
      setIsCreatingJob(false)

      if (!newJob) {
        toast({
          title: 'Job creation failed',
          description: 'Failed to create processing job',
          variant: 'destructive',
        })
        return
      }

      toast({
        title: 'Job created',
        description: 'Processing configuration...',
      })

      // Start polling
      startPolling(newJob.id)
    } catch (error) {
      setIsCreatingJob(false)
      toast({
        title: 'Upload failed',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      })
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }

  const getStatusBadge = (status: Job['status']) => {
    switch (status) {
      case 'pending':
        return (
          <Badge variant="secondary">
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            Pending
          </Badge>
        )
      case 'running':
        return (
          <Badge className="bg-yellow-500">
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            Processing
          </Badge>
        )
      case 'completed':
        return (
          <Badge className="bg-green-500">
            <CheckCircle className="mr-1 h-3 w-3" />
            Completed
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="destructive">
            <XCircle className="mr-1 h-3 w-3" />
            Failed
          </Badge>
        )
    }
  }

  // Show toast when job completes or fails and fetch graph if completed
  useEffect(() => {
    if (job?.status === 'completed') {
      toast({
        title: 'Success!',
        description: 'Graph generated successfully',
      })
      // Fetch the graph for this job
      const fetchGraphForJob = async () => {
        if (currentProject) {
          try {
            const graphs = await api.getProjectGraphs(currentProject.id)
            if (graphs && graphs.length > 0) {
              // Find the graph with matching job_id
              const graph = graphs.find((g) => g.job_id === job.id)
              if (graph) {
                setGraphId(graph.id)
              } else {
                // Fallback to the most recent graph
                setGraphId(graphs[0].id)
              }
            }
          } catch (error) {
            console.error('Failed to fetch graphs:', error)
          }
        }
      }
      fetchGraphForJob()
    } else if (job?.status === 'failed') {
      toast({
        title: 'Job failed',
        description: 'See logs for details',
        variant: 'destructive',
      })
    }
  }, [job?.status, job?.id, currentProject])

  if (!currentProject) {
    return (
      <div>
        <h1 className="text-3xl font-bold mb-6">Upload Configuration</h1>
        <Alert>
          <AlertDescription>
            Please{' '}
            <Link to="/" className="underline font-medium">
              select a project
            </Link>{' '}
            first before uploading files.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Upload Configuration</h1>

      {/* Project Info */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-muted-foreground">Project:</span>
          <span className="font-semibold">{currentProject.name}</span>
        </div>
        {currentProject.labels && currentProject.labels.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">Labels:</span>
            <div className="flex flex-wrap gap-1">
              {currentProject.labels.map((label, index) => (
                <Badge key={index} variant="outline">
                  {label}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Upload Section */}
      {!uploadResult && !job && (
        <div className="space-y-6">
          {/* Drop Zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
              dragActive
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-muted-foreground/50'
            }`}
            onDragOver={handleDragOver}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e: React.KeyboardEvent<HTMLDivElement>) => {
              if (e.key === 'Enter' || e.key === ' ') {
                fileInputRef.current?.click()
              }
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip,.tar.gz,.tar,.tgz"
              onChange={handleFileInputChange}
              className="hidden"
            />
            <FileArchive className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-2">
              Drag and drop your Splunk configuration archive here
            </p>
            <p className="text-sm text-muted-foreground mb-4">or click to browse</p>
            <div className="text-xs text-muted-foreground space-y-1">
              <p>Supported formats: .zip, .tar.gz, .tar, .tgz</p>
              <p>Maximum file size: 2GB</p>
            </div>
          </div>

          {/* Selected File Display */}
          {selectedFile && (
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileArchive className="h-8 w-8 text-muted-foreground" />
                  <div>
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedFile(null)}
                  disabled={isUploading}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              
              {/* Upload Progress */}
              {isUploading && uploadProgress > 0 && (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Uploading...</span>
                    <span className="font-medium">{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} className="h-2" />
                </div>
              )}
              
              <div className="mt-4">
                <Button onClick={handleUpload} disabled={isUploading} className="w-full">
                  {isUploading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Uploading... {uploadProgress}%
                    </>
                  ) : (
                    <>
                      <UploadIcon className="mr-2 h-4 w-4" />
                      Upload and Process
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {uploadError && (
            <Alert variant="destructive">
              <AlertDescription>{uploadError}</AlertDescription>
            </Alert>
          )}
        </div>
      )}

      {/* Job Status Section */}
      {(uploadResult || job) && (
        <div className="space-y-6">
          {/* Upload Info */}
          {uploadResult && (
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">Upload Details</h3>
                <Badge variant="outline">Upload #{uploadResult.id}</Badge>
              </div>
              <div className="text-sm space-y-1">
                <p>
                  <span className="text-muted-foreground">File:</span> {uploadResult.filename}
                </p>
                <p>
                  <span className="text-muted-foreground">Size:</span>{' '}
                  {formatFileSize(uploadResult.size)}
                </p>
                <p>
                  <span className="text-muted-foreground">Uploaded:</span>{' '}
                  {new Date(uploadResult.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          )}

          {/* Job Status */}
          {job && (
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">Processing Job</h3>
                  {getStatusBadge(job.status)}
                </div>
                <Badge variant="outline">Job #{job.id}</Badge>
              </div>

              {isCreatingJob && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating job...
                </div>
              )}

              {isPolling && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Polling for updates...
                </div>
              )}

              {job.log && (
                <div className="mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowLogsDialog(true)}
                  >
                    View Logs
                  </Button>
                </div>
              )}

              {job.status === 'completed' && graphId && (
                <div className="mt-4">
                  <Button onClick={() => navigate(`/graphs/${graphId}`)} className="w-full">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View Graph
                  </Button>
                </div>
              )}

              {job.status === 'failed' && (
                <Alert variant="destructive" className="mt-4">
                  <AlertDescription>
                    Job failed. {job.log ? 'Check logs for details.' : 'No error details available.'}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {/* Upload Another File */}
          <Button
            variant="outline"
            onClick={() => {
              setSelectedFile(null)
              setUploadResult(null)
              setGraphId(null)
              resetJobPolling()
            }}
          >
            Upload Another File
          </Button>
        </div>
      )}

      {/* Logs Dialog */}
      {job?.log && (
        <Dialog open={showLogsDialog} onOpenChange={setShowLogsDialog}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle>Job Logs</DialogTitle>
              <DialogDescription>Processing logs for Job #{job.id}</DialogDescription>
            </DialogHeader>
            <div className="flex-1 overflow-auto">
              <pre className="text-xs font-mono bg-muted p-4 rounded-md whitespace-pre-wrap">
                {job.log}
              </pre>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}

