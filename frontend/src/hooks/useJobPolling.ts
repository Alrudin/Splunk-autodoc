import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '@/lib/api'
import type { Job } from '@/types'

interface UseJobPollingReturn {
  job: Job | null
  isPolling: boolean
  error: string | null
  startPolling: (jobId: number) => void
  stopPolling: () => void
  reset: () => void
}

const POLL_INTERVAL = 2000 // 2 seconds

export function useJobPolling(initialJobId?: number): UseJobPollingReturn {
  const [job, setJob] = useState<Job | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setIsPolling(false)
  }

  const reset = () => {
    stopPolling()
    setJob(null)
    setError(null)
  }

  const fetchJob = async (id: number) => {
    try {
      setError(null)
      const jobData = await api.getJob(id)
      
      if (jobData) {
        setJob(jobData)
        
        // Check if job is in terminal state
        if (jobData.status === 'completed' || jobData.status === 'failed') {
          stopPolling()
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch job status'
      setError(errorMessage)
      console.error('Failed to fetch job:', err)
      stopPolling()
    }
  }

  const startPolling = useCallback((id: number) => {
    // Stop any existing polling
    stopPolling()
    
    // Start polling
    setIsPolling(true)
    setError(null)
    
    // Fetch immediately
    fetchJob(id)
    
    // Set up interval for polling
    intervalRef.current = setInterval(() => {
      fetchJob(id)
    }, POLL_INTERVAL)
  }, [stopPolling, setIsPolling, setError, fetchJob])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [])

  // Track last polled jobId to avoid unnecessary restarts
  const lastPolledJobIdRef = useRef<number | undefined>(undefined)

  // Start polling if initialJobId was provided and changed
  useEffect(() => {
    if (
      initialJobId &&
      initialJobId !== lastPolledJobIdRef.current
    ) {
      startPolling(initialJobId)
      lastPolledJobIdRef.current = initialJobId
    }
  }, [initialJobId, startPolling])

  return {
    job,
    isPolling,
    error,
    startPolling,
    stopPolling,
    reset,
  }
}
