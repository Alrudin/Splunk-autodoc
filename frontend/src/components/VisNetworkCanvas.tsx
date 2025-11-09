import { useRef, useEffect, useMemo, useImperativeHandle, forwardRef } from 'react'
import { Network, Options, Node } from 'vis-network/standalone'
import { edgeIdFromEdge } from '@/lib/edgeId'
import type { Host, Edge } from '@/types'

export interface VisNetworkHandle {
  focusNode: (nodeId: string) => void
  focusEdge: (edgeId: string) => void
}

interface VisNetworkCanvasProps {
  hosts: Host[]
  edges: Edge[]
  layoutMode: 'topology' | 'hierarchical'
  onNodeSelect: (nodeId: string | null) => void
  onEdgeSelect: (edgeId: string | null) => void
  selectedNodeId?: string | null
  selectedEdgeId?: string | null
  onEdgeMapUpdate?: (edgeMap: Map<string, Edge>) => void
}

// Color mappings for roles
const roleColors: Record<string, string> = {
  universal_forwarder: '#3b82f6', // blue
  heavy_forwarder: '#22c55e', // green
  indexer: '#f97316', // orange
  search_head: '#a855f7', // purple
  unknown: '#6b7280', // gray
}

// Color mappings for protocols
const protocolColors: Record<string, string> = {
  splunktcp: '#3b82f6', // blue
  http_event_collector: '#22c55e', // green
  syslog: '#eab308', // yellow
  tcp: '#6b7280', // gray
  udp: '#9ca3af', // light gray
}

export const VisNetworkCanvas = forwardRef<VisNetworkHandle, VisNetworkCanvasProps>(
  (
    {
      hosts,
      edges,
      layoutMode,
      onNodeSelect,
      onEdgeSelect,
      selectedNodeId,
      selectedEdgeId,
      onEdgeMapUpdate,
    },
    ref
  ) => {
    const containerRef = useRef<HTMLDivElement>(null)
    const networkRef = useRef<Network | null>(null)
    const minimapCanvasRef = useRef<HTMLCanvasElement>(null)
    const showMinimap = true // Can be made configurable via props in the future

  // Transform hosts to vis-network nodes
  const nodes = useMemo<Node[]>(() => {
    return hosts.map((host) => {
      // Determine node color based on primary role
      const primaryRole = host.roles[0] || 'unknown'
      const color = roleColors[primaryRole] || roleColors.unknown

      // Assign hierarchical level based on role for proper left-to-right layout
      // Input sources/UF = 1, HF = 2, Indexers = 3, Search Heads = 4, Unknown = 2 (middle)
      let level: number | undefined
      if (layoutMode === 'hierarchical') {
        if (primaryRole === 'universal_forwarder') {
          level = 1
        } else if (primaryRole === 'heavy_forwarder') {
          level = 2
        } else if (primaryRole === 'indexer') {
          level = 3
        } else if (primaryRole === 'search_head') {
          level = 4
        } else {
          level = 2 // Default to middle level for unknown roles
        }
      }

      // Create tooltip with host information
      const tooltip = `
        <div style="padding: 8px;">
          <strong>${host.id}</strong><br/>
          <strong>Roles:</strong> ${host.roles.join(', ') || 'none'}<br/>
          <strong>Apps:</strong> ${host.apps.length || 0}<br/>
          ${host.labels.length > 0 ? `<strong>Labels:</strong> ${host.labels.join(', ')}<br/>` : ''}
        </div>
      `

      return {
        id: host.id,
        label: host.id,
        title: tooltip,
        color,
        shape: 'box',
        font: { size: 14 },
        level, // Include level for hierarchical layout
      }
    })
  }, [hosts, layoutMode])

  // Transform edges to vis-network edges and build edge ID mapping
  const { visEdges, edgeMap } = useMemo(() => {
    const map = new Map<string, Edge>()
    const edgeCount = edges.length
    const visEdgeList = edges.map((edge) => {
      // Generate robust unique edge ID using shared utility
      const edgeId = edgeIdFromEdge(edge)

      // Store edge in map for lookup
      map.set(edgeId, edge)

      // Determine edge color based on protocol
      const color = protocolColors[edge.protocol] || protocolColors.tcp

      // Create tooltip with edge information
      const tooltip = `
        <div style="padding: 8px;">
          <strong>${edge.src_host} → ${edge.dst_host}</strong><br/>
          <strong>Protocol:</strong> ${edge.protocol}<br/>
          <strong>TLS:</strong> ${edge.tls === true ? 'Yes' : edge.tls === false ? 'No' : 'Unknown'}<br/>
          <strong>Indexes:</strong> ${edge.indexes.join(', ') || 'none'}<br/>
          <strong>Sourcetypes:</strong> ${edge.sourcetypes.length || 0}<br/>
          <strong>Weight:</strong> ${edge.weight}<br/>
        </div>
      `

      // Scale width based on weight (1-10)
      const width = Math.max(1, Math.min(10, edge.weight))

      return {
        id: edgeId,
        from: edge.src_host,
        to: edge.dst_host,
        // Only show labels for small graphs (< 1000 edges) for performance
        label: edgeCount < 1000 ? edge.protocol : undefined,
        title: tooltip,
        color,
        width,
        dashes: edge.tls === false, // Dashed if no TLS
        arrows: 'to',
      }
    })
    return { visEdges: visEdgeList, edgeMap: map }
  }, [edges])

  // Notify parent component of edge map updates
  useEffect(() => {
    if (onEdgeMapUpdate) {
      onEdgeMapUpdate(edgeMap)
    }
  }, [edgeMap, onEdgeMapUpdate])

  // Configuration for topology (force-directed) layout
  const topologyOptions: Options = useMemo(
    () => ({
      layout: { improvedLayout: true },
      physics: {
        enabled: true,
        stabilization: { iterations: 200, fit: true },
        barnesHut: {
          gravitationalConstant: -8000,
          springLength: 200,
          springConstant: 0.04,
        },
        solver: 'barnesHut',
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: { enabled: true },
        zoomView: true,
      },
      manipulation: { enabled: false },
      configure: { enabled: false },
    }),
    []
  )

  // Configuration for hierarchical layout
  const hierarchicalOptions: Options = useMemo(
    () => ({
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'LR', // Left to right
          sortMethod: 'directed',
          levelSeparation: 200,
          nodeSpacing: 150,
          treeSpacing: 200,
          blockShifting: true,
          edgeMinimization: true,
        },
      },
      physics: { enabled: false },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: { enabled: true },
        zoomView: true,
      },
      manipulation: { enabled: false },
      configure: { enabled: false },
    }),
    []
  )

  // Get current options based on layout mode
  const currentOptions = layoutMode === 'topology' ? topologyOptions : hierarchicalOptions

  // Initialize vis-network once on mount (empty deps)
  useEffect(() => {
    if (!containerRef.current) return

    try {
      const data = { nodes: [], edges: [] }
      const network = new Network(containerRef.current, data, currentOptions)
      networkRef.current = network

      // Event handlers - registered only once
      network.on('selectNode', (params) => {
        onNodeSelect(params.nodes[0] || null)
      })

      network.on('selectEdge', (params) => {
        onEdgeSelect(params.edges[0] || null)
      })

      network.on('deselectNode', () => {
        onNodeSelect(null)
      })

      network.on('deselectEdge', () => {
        onEdgeSelect(null)
      })

      // Performance optimization: disable physics after stabilization
      network.on('stabilizationIterationsDone', () => {
        network.setOptions({ physics: { enabled: false } })
      })

      // Performance optimization: hide edges during drag only for large graphs
      network.on('dragStart', () => {
        if (edges.length > 1000) {
          network.setOptions({ edges: { hidden: true } })
        }
      })

      network.on('dragEnd', () => {
        if (edges.length > 1000) {
          network.setOptions({ edges: { hidden: false } })
        }
      })

      // Cleanup on unmount only
      return () => {
        network.destroy()
        networkRef.current = null
      }
    } catch (err) {
      console.error('Error initializing vis-network:', err)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty deps - create once on mount

  // Update data when nodes or edges change
  useEffect(() => {
    const network = networkRef.current
    if (!network) return

    try {
      network.setData({ nodes, edges: visEdges })
    } catch (err) {
      console.error('Error updating vis-network data:', err)
    }
  }, [nodes, visEdges])

  // Update options when layout mode changes
  useEffect(() => {
    const network = networkRef.current
    if (!network) return

    try {
      network.setOptions(currentOptions)
      
      // Re-enable physics for topology mode after layout switch
      if (layoutMode === 'topology') {
        network.setOptions({ physics: { enabled: true } })
      }
    } catch (err) {
      console.error('Error updating vis-network options:', err)
    }
  }, [currentOptions, layoutMode])

  // Update selection when props change (inspector → graph highlighting)
  useEffect(() => {
    const network = networkRef.current
    if (!network) return

    if (selectedNodeId) {
      network.selectNodes([selectedNodeId])
    }
  }, [selectedNodeId])

  useEffect(() => {
    const network = networkRef.current
    if (!network) return

    if (selectedEdgeId) {
      network.selectEdges([selectedEdgeId])
    }
  }, [selectedEdgeId])

  // Minimap rendering
  useEffect(() => {
    const network = networkRef.current
    const canvas = minimapCanvasRef.current
    if (!network || !canvas || !showMinimap) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const updateMinimap = () => {
      const positions = network.getPositions()
      const scale = network.getScale()
      const viewPosition = network.getViewPosition()

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Calculate bounds
      const nodeIds = Object.keys(positions)
      if (nodeIds.length === 0) return

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
      nodeIds.forEach((id) => {
        const pos = positions[id]
        minX = Math.min(minX, pos.x)
        maxX = Math.max(maxX, pos.x)
        minY = Math.min(minY, pos.y)
        maxY = Math.max(maxY, pos.y)
      })

      const graphWidth = maxX - minX
      const graphHeight = maxY - minY
      const scaleX = canvas.width / graphWidth
      const scaleY = canvas.height / graphHeight
      const minimapScale = Math.min(scaleX, scaleY) * 0.9

      // Draw nodes
      ctx.fillStyle = 'rgba(59, 130, 246, 0.6)'
      nodeIds.forEach((id) => {
        const pos = positions[id]
        const x = (pos.x - minX) * minimapScale + 5
        const y = (pos.y - minY) * minimapScale + 5
        ctx.beginPath()
        ctx.arc(x, y, 2, 0, Math.PI * 2)
        ctx.fill()
      })

      // Draw viewport rectangle
      const viewWidth = (canvas.width / scale) * minimapScale
      const viewHeight = (canvas.height / scale) * minimapScale
      const viewX = (-viewPosition.x - minX) * minimapScale + 5
      const viewY = (-viewPosition.y - minY) * minimapScale + 5

      ctx.strokeStyle = 'rgba(239, 68, 68, 0.8)'
      ctx.lineWidth = 2
      ctx.strokeRect(viewX, viewY, viewWidth, viewHeight)
    }

    // Update minimap on various events
    network.on('stabilized', updateMinimap)
    network.on('dragEnd', updateMinimap)
    network.on('zoom', updateMinimap)

    // Initial render
    updateMinimap()

    return () => {
      network.off('stabilized', updateMinimap)
      network.off('dragEnd', updateMinimap)
      network.off('zoom', updateMinimap)
    }
  }, [showMinimap])

  // Expose focus methods to parent via ref
  useImperativeHandle(ref, () => ({
    focusNode: (nodeId: string) => {
      if (!networkRef.current) return

      // Select the node
      networkRef.current.selectNodes([nodeId])

      // Focus on the node with animation
      networkRef.current.focus(nodeId, {
        scale: 1.5,
        animation: {
          duration: 500,
          easingFunction: 'easeInOutQuad',
        },
      })
    },
    focusEdge: (edgeId: string) => {
      if (!networkRef.current) return

      // Select the edge
      networkRef.current.selectEdges([edgeId])

      // Get edge data to find connected nodes
      const edge = edgeMap.get(edgeId)
      if (edge) {
        // Focus on the edge by centering on its connected nodes
        networkRef.current.fit({
          nodes: [edge.src_host, edge.dst_host],
          animation: {
            duration: 500,
            easingFunction: 'easeInOutQuad',
          },
        })
      } else {
        // Fallback if edge not found - just fit to show everything
        networkRef.current.fit({
          animation: {
            duration: 500,
            easingFunction: 'easeInOutQuad',
          },
        })
      }
    },
  }), [edgeMap])

  return (
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        className="w-full h-full border rounded-md bg-background"
        style={{ height: 'calc(100vh - 200px)' }}
      />
      {showMinimap && (
        <canvas
          ref={minimapCanvasRef}
          width={200}
          height={150}
          className="absolute bottom-4 right-4 border-2 border-border rounded bg-background/90 shadow-lg"
          style={{ pointerEvents: 'none' }}
        />
      )}
    </div>
  )
})

VisNetworkCanvas.displayName = 'VisNetworkCanvas'
