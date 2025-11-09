import { StateCreator } from 'zustand'
import type { Graph, Finding } from '@/types'

export interface GraphSlice {
  currentGraph: Graph | null
  findings: Finding[]
  isLoading: boolean
  error: string | null
  setCurrentGraph: (graph: Graph | null) => void
  setFindings: (findings: Finding[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const createGraphSlice: StateCreator<GraphSlice, [], [], GraphSlice> = (set) => ({
  currentGraph: null,
  findings: [],
  isLoading: false,
  error: null,
  setCurrentGraph: (graph) => set({ currentGraph: graph }),
  setFindings: (findings) => set({ findings }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
})
