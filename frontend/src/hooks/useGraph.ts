import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import { useStore } from '@/store'
import type { Graph, Finding, GraphQueryParams } from '@/types'

export interface UseGraphReturn {
  graph: Graph | null
  findings: Finding[]
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
  queryGraph: (params: GraphQueryParams) => Promise<void>
  fetchFindings: () => Promise<void>
}

/**
 * Custom React hook for graph data fetching and management.
 * Follows the useProjects pattern with Zustand store integration.
 * 
 * @param graphId - The ID of the graph to fetch (from useParams)
 * @returns Graph data, findings, loading/error states, and operations
 */
export function useGraph(graphId: string | undefined): UseGraphReturn {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { currentGraph, setCurrentGraph, findings, setFindings } = useStore((state) => ({
    currentGraph: state.currentGraph,
    setCurrentGraph: state.setCurrentGraph,
    findings: state.findings,
    setFindings: state.setFindings,
  }))

  const fetchGraph = useCallback(async () => {
    if (!graphId) return

    setIsLoading(true)
    setError(null)

    try {
      const graph = await api.getGraph(Number(graphId))
      if (graph) {
        setCurrentGraph(graph)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch graph'
      setError(message)
      console.error('Error fetching graph:', err)
    } finally {
      setIsLoading(false)
    }
  }, [graphId, setCurrentGraph])

  const fetchFindings = useCallback(async () => {
    if (!graphId) return

    try {
      const graphFindings = await api.getGraphFindings(Number(graphId))
      if (graphFindings) {
        setFindings(graphFindings)
      }
    } catch (err) {
      console.error('Error fetching findings:', err)
      // Don't set error state for findings fetch failure (non-critical)
    }
  }, [graphId, setFindings])

  const queryGraphWithParams = useCallback(async (params: GraphQueryParams) => {
    if (!graphId) return

    setIsLoading(true)
    setError(null)

    try {
      const graph = await api.queryGraph(Number(graphId), params)
      if (graph) {
        setCurrentGraph(graph)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to query graph'
      setError(message)
      console.error('Error querying graph:', err)
    } finally {
      setIsLoading(false)
    }
  }, [graphId, setCurrentGraph])

  const refetch = useCallback(async () => {
    await fetchGraph()
    await fetchFindings()
  }, [fetchGraph, fetchFindings])

  // Fetch graph and findings on mount or when graphId changes
  useEffect(() => {
    if (!graphId) return;
    // Call local async functions directly to avoid dependency cycle
    (async () => {
      await fetchGraph();
      await fetchFindings();
    })();
  }, [graphId])

  return {
    graph: currentGraph,
    findings,
    isLoading,
    error,
    refetch,
    queryGraph: queryGraphWithParams,
    fetchFindings,
  }
}
