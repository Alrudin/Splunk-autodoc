import { StateCreator } from 'zustand'

export interface GraphFilters {
  host?: string
  index?: string
  protocol?: string
  role?: string
  tls?: boolean
  severity?: 'error' | 'warning' | 'info'
}

export interface FilterSlice {
  filters: GraphFilters
  setFilters: (filters: GraphFilters) => void
  updateFilter: <K extends keyof GraphFilters>(key: K, value: GraphFilters[K]) => void
  clearFilters: () => void
}

export const createFilterSlice: StateCreator<FilterSlice, [], [], FilterSlice> = (set) => ({
  filters: {},
  setFilters: (filters) => set({ filters }),
  updateFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    })),
  clearFilters: () => set({ filters: {} }),
})
