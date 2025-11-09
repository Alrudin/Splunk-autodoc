import { useMemo } from 'react'
import type { Finding, Edge } from '@/types'
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
import { AlertCircle, AlertTriangle, Info, X, Filter, Focus } from 'lucide-react'

interface EdgeInspectorProps {
  edgeId: string | null
  edgeMap: Map<string, Edge> | null
  findings: Finding[]
  onClose?: () => void
  onFilterByProtocol?: (protocol: string) => void
  onFilterByIndex?: (index: string) => void
  onFocus?: (edgeId: string) => void
}

export function EdgeInspector({ edgeId, edgeMap, findings, onClose, onFilterByProtocol, onFilterByIndex, onFocus }: EdgeInspectorProps) {
  // Use edge map for direct lookup - no parsing needed
  const edgeData = useMemo(() => {
    if (!edgeId || !edgeMap) return null

    // Direct lookup of edge by ID
    const edge = edgeMap.get(edgeId)
    if (!edge) return null

    const srcHost = edge.src_host
    const dstHost = edge.dst_host

    // Filter findings strictly where BOTH src_host AND dst_host match
    // Use type guard to safely check context fields
    const edgeFindings = findings.filter((f) => {
      const context = f.context
      // Only include findings that specifically reference both hosts of this edge
      if (context.src_host && context.dst_host) {
        return context.src_host === srcHost && context.dst_host === dstHost
      }
      // Handle single-host findings that might affect this edge
      if (context.host) {
        return context.host === srcHost || context.host === dstHost
      }
      // Skip findings without relevant host context
      return false
    })

    return {
      edge,
      srcHost,
      dstHost,
      edgeFindings,
    }
  }, [edgeId, edgeMap, findings])

  if (!edgeId) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full">
          <p className="text-muted-foreground text-center">
            Select an edge to view details
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!edgeData) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full">
          <p className="text-destructive text-center">Edge not found</p>
        </CardContent>
      </Card>
    )
  }

  const { edge, srcHost, dstHost, edgeFindings } = edgeData

  // Severity icon mapping
  const severityIcons = {
    error: <AlertCircle className="h-4 w-4 text-destructive" />,
    warning: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    info: <Info className="h-4 w-4 text-blue-500" />,
  }

  // TLS badge color
  const tlsBadgeVariant = edge.tls === true ? 'default' : edge.tls === false ? 'destructive' : 'secondary'

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm break-all">
            {srcHost} → {dstHost}
          </CardTitle>
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
        <div className="flex gap-2 mt-2 flex-wrap">
          {onFilterByProtocol && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => onFilterByProtocol(edge.protocol)}
            >
              <Filter className="h-3 w-3 mr-1" />
              Filter by protocol
            </Button>
          )}
          {onFilterByIndex && edge.indexes.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => onFilterByIndex(edge.indexes[0])}
            >
              <Filter className="h-3 w-3 mr-1" />
              Filter by index
            </Button>
          )}
          {onFocus && edgeId && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => onFocus(edgeId)}
            >
              <Focus className="h-3 w-3 mr-1" />
              Focus
            </Button>
          )}
        </div>
      </CardHeader>

      <ScrollArea className="flex-1">
        <CardContent className="space-y-4">
          {/* Protocol & Path */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Connection</h3>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{edge.protocol}</Badge>
              <Badge variant="secondary">{edge.path_kind}</Badge>
              <Badge variant={tlsBadgeVariant}>
                TLS: {edge.tls === true ? 'Yes' : edge.tls === false ? 'No' : 'Unknown'}
              </Badge>
            </div>
          </div>

          {/* Weight & Confidence */}
          <div className="flex gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Weight: </span>
              <span className="font-medium">{edge.weight}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Confidence: </span>
              <Badge variant="outline" className="text-xs">
                {edge.confidence}
              </Badge>
            </div>
          </div>

          <Separator />

          {/* Sources */}
          {edge.sources.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">
                Sources ({edge.sources.length})
              </h3>
              <div className="space-y-1">
                {edge.sources.slice(0, 10).map((source, idx) => (
                  <div key={idx} className="text-xs text-muted-foreground font-mono">
                    {source}
                  </div>
                ))}
                {edge.sources.length > 10 && (
                  <p className="text-xs text-muted-foreground">
                    ...and {edge.sources.length - 10} more
                  </p>
                )}
              </div>
            </div>
          )}

          <Separator />

          {/* Sourcetypes */}
          {edge.sourcetypes.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">
                Sourcetypes ({edge.sourcetypes.length})
              </h3>
              <div className="flex flex-wrap gap-1">
                {edge.sourcetypes.slice(0, 15).map((st) => (
                  <Badge key={st} variant="outline" className="text-xs">
                    {st}
                  </Badge>
                ))}
                {edge.sourcetypes.length > 15 && (
                  <span className="text-xs text-muted-foreground">
                    +{edge.sourcetypes.length - 15} more
                  </span>
                )}
              </div>
            </div>
          )}

          <Separator />

          {/* Indexes */}
          {edge.indexes.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">
                Indexes ({edge.indexes.length})
              </h3>
              <div className="flex flex-wrap gap-1">
                {edge.indexes.map((idx) => (
                  <Badge key={idx} className="text-xs bg-orange-100 text-orange-800">
                    {idx}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <Separator />

          {/* Filters/Transforms */}
          {edge.filters.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">
                Transforms ({edge.filters.length})
              </h3>
              <div className="space-y-1">
                {edge.filters.map((filter, idx) => (
                  <div key={idx} className="text-xs text-muted-foreground font-mono">
                    {filter}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Drop Rules */}
          {edge.drop_rules.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                  Drop Rules ({edge.drop_rules.length})
                  <Badge variant="destructive" className="text-xs">
                    Warning
                  </Badge>
                </h3>
                <div className="space-y-1">
                  {edge.drop_rules.map((rule, idx) => (
                    <div key={idx} className="text-xs text-destructive font-mono">
                      {rule}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* App Contexts */}
          {edge.app_contexts.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <h3 className="text-sm font-semibold">
                  App Contexts ({edge.app_contexts.length})
                </h3>
                <div className="flex flex-wrap gap-1">
                  {edge.app_contexts.map((app) => (
                    <Badge key={app} variant="secondary" className="text-xs">
                      {app}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Findings */}
          {edgeFindings.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <h3 className="text-sm font-semibold">
                  Findings ({edgeFindings.length})
                </h3>
                <div className="space-y-2">
                  {edgeFindings.slice(0, 5).map((finding) => (
                    <div
                      key={finding.id}
                      className="p-2 border rounded-md space-y-1"
                    >
                      <div className="flex items-center gap-2">
                        {severityIcons[finding.severity]}
                        <Badge
                          variant={
                            finding.severity === 'error'
                              ? 'destructive'
                              : 'secondary'
                          }
                          className="text-xs"
                        >
                          {finding.severity}
                        </Badge>
                        <span className="text-xs font-mono">{finding.code}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {finding.message}
                      </p>
                    </div>
                  ))}
                  {edgeFindings.length > 5 && (
                    <p className="text-xs text-muted-foreground">
                      ...and {edgeFindings.length - 5} more findings
                    </p>
                  )}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </ScrollArea>
    </Card>
  )
}
