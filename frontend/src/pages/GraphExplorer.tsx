import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Filter as FilterIcon, Loader2, Download, FileJson, FileImage, FileText, AlertTriangle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'
import { edgeIdFromEdge } from '@/lib/edgeId'
import type { Edge } from '@/types'

export function GraphExplorerPage() {
  const { graphId } = useParams<{ graphId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { graph, findings, isLoading, error } = useGraph(graphId)
  const filters = useStore((state) => state.filters)
  const updateFilter = useStore((state) => state.updateFilter)
  const visNetworkRef = useRef<VisNetworkHandle>(null)
  const { toast } = useToast()

  // Local state
  const [layoutMode, setLayoutMode] = useState<'topology' | 'hierarchical'>('topology')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [showFilters, setShowFilters] = useState(true)
  const [edgeMap, setEdgeMap] = useState<Map<string, Edge> | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [exportFormat, setExportFormat] = useState<'dot' | 'json' | 'png' | 'pdf'>('png')

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

  // Handle highlighting from Findings page navigation
  useEffect(() => {
    if (location.state?.highlightHosts && Array.isArray(location.state.highlightHosts)) {
      const hosts = location.state.highlightHosts as string[]

      // Early return if edgeMap is not ready yet (race condition prevention)
      // Keep state so effect re-evaluates when edgeMap becomes available
      if (!edgeMap) {
        return
      }

      let wasHighlighted = false

      // If we have src_host and dst_host, try to select the edge
      if (hosts.length >= 2 && hosts[0] && hosts[1]) {
        // Find edge between these hosts in filtered edges
        const edge = filteredEdges.find(
          (e) => e.src_host === hosts[0] && e.dst_host === hosts[1]
        )
        
        if (edge) {
          // Edge found in filtered view - highlight it
          // Generate edge ID using shared utility
          const edgeId = edgeIdFromEdge(edge)
          setSelectedEdgeId(edgeId)
          // Focus on the edge in the graph
          visNetworkRef.current?.focusEdge(edgeId)
          wasHighlighted = true

          // Show success toast
          if (location.state.code) {
            toast({
              title: 'Finding highlighted',
              description: `Showing ${location.state.code} finding in graph`,
            })
          }
        } else {
          // Edge not found in filtered view - fallback to focusing both nodes
          // Check if both nodes exist in filtered hosts
          const srcNodeExists = filteredHosts.some((h) => h.id === hosts[0])
          const dstNodeExists = filteredHosts.some((h) => h.id === hosts[1])

          if (srcNodeExists && dstNodeExists) {
            // Both nodes exist - focus on source node and show warning
            setSelectedNodeId(hosts[0])
            visNetworkRef.current?.focusNode(hosts[0])
            wasHighlighted = true

            toast({
              title: 'Edge hidden by filters',
              description: `The edge from ${hosts[0]} to ${hosts[1]} is hidden by current filters. Showing source host instead.`,
              variant: 'default',
            })
          } else if (srcNodeExists) {
            // Only source exists
            setSelectedNodeId(hosts[0])
            visNetworkRef.current?.focusNode(hosts[0])
            wasHighlighted = true

            toast({
              title: 'Target hidden by filters',
              description: `${hosts[1]} is hidden by current filters. Showing ${hosts[0]} instead.`,
              variant: 'default',
            })
          } else if (dstNodeExists) {
            // Only destination exists
            setSelectedNodeId(hosts[1])
            visNetworkRef.current?.focusNode(hosts[1])
            wasHighlighted = true

            toast({
              title: 'Source hidden by filters',
              description: `${hosts[0]} is hidden by current filters. Showing ${hosts[1]} instead.`,
              variant: 'default',
            })
          } else {
            // Neither node exists in filtered view
            toast({
              title: 'Finding not visible',
              description: `Both ${hosts[0]} and ${hosts[1]} are hidden by current filters. Clear filters to view this finding.`,
              variant: 'destructive',
            })
          }
        }
      } else if (hosts.length === 1 && hosts[0]) {
        // Single host - select the node if it exists
        const nodeExists = filteredHosts.some((h) => h.id === hosts[0])
        
        if (nodeExists) {
          setSelectedNodeId(hosts[0])
          visNetworkRef.current?.focusNode(hosts[0])
          wasHighlighted = true

          // Show success toast
          if (location.state.code) {
            toast({
              title: 'Finding highlighted',
              description: `Showing ${location.state.code} finding in graph`,
            })
          }
        } else {
          // Node hidden by filters
          toast({
            title: 'Finding not visible',
            description: `${hosts[0]} is hidden by current filters. Clear filters to view this finding.`,
            variant: 'destructive',
          })
        }
      }

      // Only clear the location state after attempting to highlight
      // This prevents race conditions where state is cleared before edgeMap is ready
      if (wasHighlighted || hosts.length === 0) {
        navigate(location.pathname, { replace: true, state: {} })
      }
    }
  }, [location.state, filteredEdges, filteredHosts, edgeMap])

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
    updateFilter('host', hostId)
  }, [updateFilter])

  const handleFilterByProtocol = useCallback((protocol: string) => {
    updateFilter('protocol', protocol as 'splunktcp' | 'http_event_collector' | 'syslog' | 'tcp' | 'udp')
  }, [updateFilter])

  const handleFilterByIndex = useCallback((index: string) => {
    updateFilter('index', index)
  }, [updateFilter])

  const handleFocusNode = useCallback((nodeId: string) => {
    visNetworkRef.current?.focusNode(nodeId)
  }, [])

  const handleFocusEdge = useCallback((edgeId: string) => {
    visNetworkRef.current?.focusEdge(edgeId)
  }, [])

  // Export handler
  const handleExport = useCallback(
    async (format: 'dot' | 'json' | 'png' | 'pdf') => {
      if (!graphId) return

      setIsExporting(true)

      try {
        // Pass current filters to export the filtered view
        // Convert filters to GraphQueryParams format
        const queryParams: {
          host?: string
          index?: string
          protocol?: string
        } = {}
        
        if (filters.host) queryParams.host = filters.host
        if (filters.index) queryParams.index = filters.index
        if (filters.protocol) queryParams.protocol = filters.protocol

        // Get export URL from API client with filters
        const exportUrl = api.exportGraph(
          Number(graphId),
          format,
          Object.keys(queryParams).length > 0 ? queryParams : undefined
        )

        // Create temporary anchor element for download
        const link = document.createElement('a')
        link.href = exportUrl
        link.download = `graph-${graphId}-${new Date().toISOString()}.${format}`
        link.target = '_blank'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)

        // Show success toast with filter context
        const hasFilters = activeFilterCount > 0
        toast({
          title: 'Export started',
          description: hasFilters
            ? `Downloading filtered graph (${activeFilterCount} filters active) as ${format.toUpperCase()}`
            : `Downloading full graph as ${format.toUpperCase()}`,
        })
      } catch (error) {
        // Show error toast
        toast({
          title: 'Export failed',
          description: error instanceof Error ? error.message : 'Failed to export graph',
          variant: 'destructive',
        })
      } finally {
        setIsExporting(false)
      }
    },
    [graphId, filters, activeFilterCount, toast]
  )

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
          {findings.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(`/graphs/${graphId}/findings`)}
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              {findings.length} Findings
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={layoutMode}
            onValueChange={(value: string) => setLayoutMode(value as 'topology' | 'hierarchical')}
          >
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
          <div className="flex items-center gap-2 ml-2 border-l pl-2">
            <Select
              value={exportFormat}
              onValueChange={(value) => setExportFormat(value as 'dot' | 'json' | 'png' | 'pdf')}
            >
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="png">
                  <div className="flex items-center">
                    <FileImage className="h-4 w-4 mr-2" />
                    PNG
                  </div>
                </SelectItem>
                <SelectItem value="pdf">
                  <div className="flex items-center">
                    <FileImage className="h-4 w-4 mr-2" />
                    PDF
                  </div>
                </SelectItem>
                <SelectItem value="dot">
                  <div className="flex items-center">
                    <FileText className="h-4 w-4 mr-2" />
                    DOT
                  </div>
                </SelectItem>
                <SelectItem value="json">
                  <div className="flex items-center">
                    <FileJson className="h-4 w-4 mr-2" />
                    JSON
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => handleExport(exportFormat)}
                    disabled={isExporting}
                  >
                    {isExporting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {activeFilterCount > 0
                    ? `Export filtered view (${activeFilterCount} filters active)`
                    : 'Export full graph'}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
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
