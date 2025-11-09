import { useMemo } from 'react'
import type { CanonicalGraph } from '@/types'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { X, Filter, Focus } from 'lucide-react'

interface NodeInspectorProps {
  nodeId: string | null
  graph: CanonicalGraph | null
  onClose?: () => void
  onFilterByHost?: (hostId: string) => void
  onFocus?: (nodeId: string) => void
}

export function NodeInspector({ nodeId, graph, onClose, onFilterByHost, onFocus }: NodeInspectorProps) {
  // Find the host and compute derived data
  const nodeData = useMemo(() => {
    if (!nodeId || !graph) return null

    const host = graph.hosts.find((h) => h.id === nodeId)
    if (!host) return null

    // Find incoming edges (inputs)
    const incomingEdges = graph.edges.filter((e) => e.dst_host === nodeId)
    const sourceHosts = [...new Set(incomingEdges.map((e) => e.src_host))]

    // Find outgoing edges (outputs)
    const outgoingEdges = graph.edges.filter((e) => e.src_host === nodeId)
    const destHosts = [...new Set(outgoingEdges.map((e) => e.dst_host))]

    // Extract unique values
    const allEdges = [...incomingEdges, ...outgoingEdges]
    const uniqueIndexes = [...new Set(allEdges.flatMap((e) => e.indexes))]
    const uniqueSourcetypes = [...new Set(allEdges.flatMap((e) => e.sourcetypes))]
    const uniqueProtocols = [...new Set(allEdges.map((e) => e.protocol))]

    return {
      host,
      incomingEdges,
      outgoingEdges,
      sourceHosts,
      destHosts,
      uniqueIndexes,
      uniqueSourcetypes,
      uniqueProtocols,
      totalDataPaths: incomingEdges.length + outgoingEdges.length,
    }
  }, [nodeId, graph])

  if (!nodeId) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full">
          <p className="text-muted-foreground text-center">
            Select a node to view details
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!nodeData) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full">
          <p className="text-destructive text-center">Node not found</p>
        </CardContent>
      </Card>
    )
  }

  const { host, incomingEdges, outgoingEdges, sourceHosts, destHosts, uniqueIndexes, uniqueSourcetypes, uniqueProtocols, totalDataPaths } = nodeData

  // Role color mapping
  const roleColors: Record<string, string> = {
    universal_forwarder: 'bg-blue-100 text-blue-800',
    heavy_forwarder: 'bg-green-100 text-green-800',
    indexer: 'bg-orange-100 text-orange-800',
    search_head: 'bg-purple-100 text-purple-800',
    unknown: 'bg-gray-100 text-gray-800',
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-lg break-all">{host.id}</CardTitle>
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 flex-shrink-0"
              onClick={onClose}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
        {/* Action buttons */}
        <div className="flex gap-2 mt-2">
          {onFilterByHost && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => onFilterByHost(host.id)}
            >
              <Filter className="h-3 w-3 mr-1" />
              Filter by this host
            </Button>
          )}
          {onFocus && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => onFocus(host.id)}
            >
              <Focus className="h-3 w-3 mr-1" />
              Focus
            </Button>
          )}
        </div>
      </CardHeader>

      <ScrollArea className="flex-1">
        <CardContent className="space-y-4">
          {/* Roles */}
          {host.roles.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">Roles</h3>
              <div className="flex flex-wrap gap-2">
                {host.roles.map((role) => (
                  <Badge
                    key={role}
                    variant="secondary"
                    className={roleColors[role] || roleColors.unknown}
                  >
                    {role.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Labels */}
          {host.labels.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">Labels</h3>
              <div className="flex flex-wrap gap-2">
                {host.labels.map((label) => (
                  <Badge key={label} variant="outline">
                    {label}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <Separator />

          {/* Apps */}
          {host.apps.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">
                Apps ({host.apps.length})
              </h3>
              <div className="space-y-1">
                {host.apps.map((app) => (
                  <div key={app} className="text-sm text-muted-foreground">
                    • {app}
                  </div>
                ))}
              </div>
            </div>
          )}

          <Separator />

          {/* Inputs (incoming edges) */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">
              Inputs ({incomingEdges.length})
            </h3>
            {incomingEdges.length > 0 ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  From {sourceHosts.length} host{sourceHosts.length !== 1 ? 's' : ''}
                </p>
                <div className="space-y-1">
                  {sourceHosts.slice(0, 5).map((srcHost) => {
                    const edges = incomingEdges.filter((e) => e.src_host === srcHost)
                    const protocols = [...new Set(edges.map((e) => e.protocol))]
                    return (
                      <div key={srcHost} className="text-sm">
                        <span className="font-medium">{srcHost}</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {protocols.map((protocol) => (
                            <Badge key={protocol} variant="outline" className="text-xs">
                              {protocol}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                  {sourceHosts.length > 5 && (
                    <p className="text-xs text-muted-foreground">
                      ...and {sourceHosts.length - 5} more
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No inputs</p>
            )}
          </div>

          <Separator />

          {/* Outputs (outgoing edges) */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">
              Outputs ({outgoingEdges.length})
            </h3>
            {outgoingEdges.length > 0 ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  To {destHosts.length} host{destHosts.length !== 1 ? 's' : ''}
                </p>
                <div className="space-y-1">
                  {destHosts.slice(0, 5).map((dstHost) => {
                    const edges = outgoingEdges.filter((e) => e.dst_host === dstHost)
                    const protocols = [...new Set(edges.map((e) => e.protocol))]
                    return (
                      <div key={dstHost} className="text-sm">
                        <span className="font-medium">{dstHost}</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {protocols.map((protocol) => (
                            <Badge key={protocol} variant="outline" className="text-xs">
                              {protocol}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                  {destHosts.length > 5 && (
                    <p className="text-xs text-muted-foreground">
                      ...and {destHosts.length - 5} more
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No outputs</p>
            )}
          </div>

          <Separator />

          {/* Statistics */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Statistics</h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total data paths:</span>
                <span className="font-medium">{totalDataPaths}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Unique indexes:</span>
                <span className="font-medium">{uniqueIndexes.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Unique sourcetypes:</span>
                <span className="font-medium">{uniqueSourcetypes.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Protocols:</span>
                <span className="font-medium">{uniqueProtocols.length}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </ScrollArea>
    </Card>
  )
}
