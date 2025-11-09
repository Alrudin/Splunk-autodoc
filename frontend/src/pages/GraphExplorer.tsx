import { useState, useMemo, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useGraph } from '@/hooks/useGraph'
import { useStore } from '@/store'
import { VisNetworkCanvas, VisNetworkHandle } from '@/components/VisNetworkCanvas'
import { FilterPanel } from '@/components/FilterPanel'
import { NodeInspector } from '@/components/NodeInspector'
import { EdgeInspector } from '@/components/EdgeInspector'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Filter as FilterIcon, Loader2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { Edge } from '@/types'

export function GraphExplorerPage() {
  const { graphId } = useParams<{ graphId: string }>()
  const { graph, findings, isLoading, error } = useGraph(graphId)
  const filters = useStore((state) => state.filters)
  const setFilters = useStore((state) => state.setFilters)
  const visNetworkRef = useRef<VisNetworkHandle>(null)

  // Local state
  const [layoutMode, setLayoutMode] = useState<'topology' | 'hierarchical'>('topology')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [showFilters, setShowFilters] = useState(true)
  const [edgeMap, setEdgeMap] = useState<Map<string, Edge> | null>(null)

  // Client-side filtering of graph data
  const { filteredHosts, filteredEdges } = useMemo(() => {
    if (!graph?.json_blob) {
      return { filteredHosts: [], filteredEdges: [] }
    }

    const { hosts, edges } = graph.json_blob

    // Filter hosts first
    let filteredHostList = hosts

    if (filters.host) {
      const searchTerm = filters.host.toLowerCase()
      filteredHostList = filteredHostList.filter((h) =>
        h.id.toLowerCase().includes(searchTerm)
      )
    }

    if (filters.role) {
      filteredHostList = filteredHostList.filter((h) =>
        h.roles.includes(filters.role!)
      )
    }

    if (filters.app) {
      const searchTerm = filters.app.toLowerCase()
      filteredHostList = filteredHostList.filter((h) =>
        h.apps.some((app) => app.toLowerCase().includes(searchTerm))
      )
    }

    // Build set of valid host IDs after host-based filtering
    const validHostIds = new Set(filteredHostList.map((h) => h.id))

    // Filter edges
    let filteredEdgeList = edges

    // Ensure edges only reference hosts that exist in filteredHostList
    // This is critical when host or role filters are active
    if (filters.host || filters.role) {
      filteredEdgeList = filteredEdgeList.filter(
        (e) => validHostIds.has(e.src_host) && validHostIds.has(e.dst_host)
      )
    }

    if (filters.protocol) {
      filteredEdgeList = filteredEdgeList.filter((e) => e.protocol === filters.protocol)
    }

    if (filters.index) {
      const searchTerm = filters.index.toLowerCase()
      filteredEdgeList = filteredEdgeList.filter((e) =>
        e.indexes.some((idx) => idx.toLowerCase().includes(searchTerm))
      )
    }

    if (filters.sourcetype) {
      const searchTerm = filters.sourcetype.toLowerCase()
      filteredEdgeList = filteredEdgeList.filter((e) =>
        e.sourcetypes.some((st) => st.toLowerCase().includes(searchTerm))
      )
    }

    if (filters.tls !== undefined) {
      filteredEdgeList = filteredEdgeList.filter((e) => e.tls === filters.tls)
    }

    // Keep only hosts that are referenced in filtered edges
    // when edge-based filters are active
    if (
      filters.protocol ||
      filters.index ||
      filters.sourcetype ||
      filters.tls !== undefined
    ) {
      const referencedHostIds = new Set<string>()
      filteredEdgeList.forEach((e) => {
        referencedHostIds.add(e.src_host)
        referencedHostIds.add(e.dst_host)
      })
      filteredHostList = filteredHostList.filter((h) =>
        referencedHostIds.has(h.id)
      )
    }

    return {
      filteredHosts: filteredHostList,
      filteredEdges: filteredEdgeList,
    }
  }, [graph, filters])

  // Count active filters
  const activeFilterCount = Object.values(filters).filter(
    (v) => v !== undefined && v !== ''
  ).length

  // Filters are managed by Zustand; no filter change callback needed

  // Handle edge map updates from VisNetworkCanvas
  const handleEdgeMapUpdate = useCallback((newEdgeMap: Map<string, Edge>) => {
    setEdgeMap(newEdgeMap)
  }, [])

  // Inspector callbacks
  const handleNodeClose = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  const handleEdgeClose = useCallback(() => {
    setSelectedEdgeId(null)
  }, [])

  const handleFilterByHost = useCallback((hostId: string) => {
    setFilters({ ...filters, host: hostId })
  }, [filters, setFilters])
  const handleFilterByHost = useCallback((hostId: string) => {
    setFilters((prev) => ({ ...prev, host: hostId }))
  }, [setFilters])

  const handleFilterByProtocol = useCallback((protocol: string) => {
    setFilters((prev) => ({
      ...prev,
      protocol: protocol as 'splunktcp' | 'http_event_collector' | 'syslog' | 'tcp' | 'udp' | ''
    }))
  }, [setFilters])

  const handleFilterByIndex = useCallback((index: string) => {
    setFilters((prev) => ({ ...prev, index }))
  }, [setFilters])
  }, [])

  const handleFocusEdge = useCallback((edgeId: string) => {
    visNetworkRef.current?.focusEdge(edgeId)
  }, [])

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-muted-foreground">Loading graph...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  // Empty state
  if (!graph?.json_blob) {
    return (
      <div className="container mx-auto p-6">
        <Alert>
          <AlertDescription>No graph data available</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header Bar */}
      <div className="flex items-center justify-between p-4 border-b flex-shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Graph Explorer</h1>
          <Badge variant="secondary">{filteredHosts.length} hosts</Badge>
          <Badge variant="secondary">{filteredEdges.length} edges</Badge>
          {activeFilterCount > 0 && (
            <Badge variant="outline">{activeFilterCount} filters</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Select value={layoutMode} onValueChange={(value: string) => setLayoutMode(value as 'topology' | 'hierarchical')}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="topology">Topology View</SelectItem>
              <SelectItem value="hierarchical">Hierarchical View</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setShowFilters(!showFilters)}
          >
            <FilterIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Filter Panel */}
        {showFilters && (
          <div className="w-80 border-r overflow-y-auto flex-shrink-0">
            <FilterPanel />
          </div>
        )}

        {/* Graph Canvas */}
        <div className="flex-1 relative">
          {filteredHosts.length === 0 || filteredEdges.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-muted-foreground">
                No data matches the current filters
              </p>
            </div>
          ) : (
            <VisNetworkCanvas
              ref={visNetworkRef}
              hosts={filteredHosts}
              edges={filteredEdges}
              layoutMode={layoutMode}
              onNodeSelect={setSelectedNodeId}
              onEdgeSelect={setSelectedEdgeId}
              selectedNodeId={selectedNodeId}
              selectedEdgeId={selectedEdgeId}
              onEdgeMapUpdate={handleEdgeMapUpdate}
            />
          )}
        </div>

        {/* Inspector Panel */}
        {(selectedNodeId || selectedEdgeId) && (
          <div className="w-80 border-l overflow-y-auto flex-shrink-0">
            <Tabs defaultValue="node" className="h-full">
              <TabsList className="w-full">
                <TabsTrigger value="node" disabled={!selectedNodeId} className="flex-1">
                  Node
                </TabsTrigger>
                <TabsTrigger value="edge" disabled={!selectedEdgeId} className="flex-1">
                  Edge
                </TabsTrigger>
              </TabsList>
              <TabsContent value="node" className="h-full">
                <NodeInspector
                  nodeId={selectedNodeId}
                  graph={graph.json_blob}
                  onClose={handleNodeClose}
                  onFilterByHost={handleFilterByHost}
                  onFocus={handleFocusNode}
                />
              </TabsContent>
              <TabsContent value="edge" className="h-full">
                <EdgeInspector
                  edgeId={selectedEdgeId}
                  edgeMap={edgeMap}
                  findings={findings}
                  onClose={handleEdgeClose}
                  onFilterByProtocol={handleFilterByProtocol}
                  onFilterByIndex={handleFilterByIndex}
                  onFocus={handleFocusEdge}
                />
              </TabsContent>
            </Tabs>
          </div>
        )}
      </div>
    </div>
  )
}
