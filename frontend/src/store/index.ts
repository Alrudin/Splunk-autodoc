import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { createProjectSlice, type ProjectSlice } from './projectSlice'
import { createGraphSlice, type GraphSlice } from './graphSlice'
import { createFilterSlice, type FilterSlice } from './filterSlice'

type StoreState = ProjectSlice & GraphSlice & FilterSlice

export const useStore = create<StoreState>()(
  devtools(
    (...a) => ({
      ...createProjectSlice(...a),
      ...createGraphSlice(...a),
      ...createFilterSlice(...a),
    }),
    { name: 'splunk-flow-store' }
  )
)

// Convenience selectors
export const useCurrentProject = () => useStore((state) => state.currentProject)
export const useCurrentGraph = () => useStore((state) => state.currentGraph)
export const useFilters = () => useStore((state) => state.filters)
