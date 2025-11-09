import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGraph } from '@/hooks/useGraph'
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, AlertTriangle, Info, ExternalLink, X, ArrowLeft, Loader2, HelpCircle } from 'lucide-react'
import type { Finding } from '@/types'

// Helper function to get Badge variant based on severity
function getSeverityVariant(severity: string): 'destructive' | 'default' | 'secondary' {
  switch (severity) {
    case 'error':
      return 'destructive'
    case 'warning':
      return 'default'
    case 'info':
      return 'secondary'
    default:
      return 'secondary'
  }
}

// Helper function to get icon based on severity
function getSeverityIcon(severity: string) {
  switch (severity) {
    case 'error':
      return <AlertCircle className="h-4 w-4" />
    case 'warning':
      return <AlertTriangle className="h-4 w-4" />
    case 'info':
      return <Info className="h-4 w-4" />
    default:
      return <Info className="h-4 w-4" />
  }
}

/**
 * Helper function to render context information with additional details
 * Returns the main display text and any additional context fields
 */
function getContextDisplay(finding: Finding): { display: string; hasExtra: boolean; extra: Record<string, unknown> } {
  const { src_host, dst_host, host, index, ...rest } = finding.context
  
  // Main display
  let display = 'N/A'
  if (src_host && dst_host) {
    display = `${src_host} → ${dst_host}`
  } else if (host) {
    display = host
  }

  // Additional context fields
  const extra: Record<string, unknown> = {}
  if (index) {
    extra.index = index
  }
  // Add any other context fields (excluding the standard ones)
  Object.entries(rest).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      extra[key] = value
    }
  })

  return {
    display,
    hasExtra: Object.keys(extra).length > 0,
    extra,
  }
}

export function FindingsPage() {
  const { graphId } = useParams<{ graphId: string }>()
  const navigate = useNavigate()
  const { findings, isLoading, error } = useGraph(graphId)

  // Local state for filters
  const [severityFilter, setSeverityFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all')
  const [codeFilter, setCodeFilter] = useState<string>('all')

  // Extract unique codes from all findings
  const uniqueCodes = useMemo(() => {
    return [...new Set(findings.map((f) => f.code))].sort()
  }, [findings])

  // Filter findings based on active filters
  const filteredFindings = useMemo(() => {
    let filtered = findings

    if (severityFilter !== 'all') {
      filtered = filtered.filter((f) => f.severity === severityFilter)
    }

    if (codeFilter !== 'all') {
      filtered = filtered.filter((f) => f.code === codeFilter)
    }

    return filtered
  }, [findings, severityFilter, codeFilter])

  // Calculate severity counts
  const errorCount = findings.filter((f) => f.severity === 'error').length
  const warningCount = findings.filter((f) => f.severity === 'warning').length
  const infoCount = findings.filter((f) => f.severity === 'info').length

  // Handle navigation to graph with highlighting
  const handleViewInGraph = (finding: Finding) => {
    const { src_host, dst_host, host } = finding.context
    const highlightHosts = [src_host, dst_host, host].filter(Boolean) as string[]

    navigate(`/graphs/${graphId}`, {
      state: {
        highlightHosts,
        findingId: finding.id,
        severity: finding.severity,
        code: finding.code,
      },
    })
  }

  // Handle clear filters
  const handleClearFilters = () => {
    setSeverityFilter('all')
    setCodeFilter('all')
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-muted-foreground">Loading findings...</p>
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

  return (
    <div className="container mx-auto p-6">
      {/* Header with navigation and stats */}
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="sm" onClick={() => navigate(`/graphs/${graphId}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Graph
        </Button>
        <h1 className="text-3xl font-bold">Findings</h1>
        <Badge variant="outline">Graph {graphId}</Badge>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="destructive">{errorCount} errors</Badge>
          <Badge variant="default">{warningCount} warnings</Badge>
          <Badge variant="secondary">{infoCount} info</Badge>
        </div>
      </div>

      {/* Filter controls */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Filters</CardTitle>
            {(severityFilter !== 'all' || codeFilter !== 'all') && (
              <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                <X className="h-4 w-4 mr-2" />
                Clear Filters
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Severity</label>
              <Select value={severityFilter} onValueChange={(value) => setSeverityFilter(value as 'all' | 'error' | 'warning' | 'info')}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by severity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Severities</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Finding Code</label>
              <Select value={codeFilter} onValueChange={setCodeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by code" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Codes</SelectItem>
                  {uniqueCodes.map((code) => (
                    <SelectItem key={code} value={code}>
                      {code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Empty state */}
      {findings.length === 0 && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>No findings for this graph</AlertDescription>
        </Alert>
      )}

      {/* No results state */}
      {findings.length > 0 && filteredFindings.length === 0 && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>No findings match the current filters</AlertDescription>
        </Alert>
      )}

      {/* Findings table */}
      {filteredFindings.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <TooltipProvider>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[120px]">Severity</TableHead>
                    <TableHead className="w-[200px]">Code</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead className="w-[200px]">Affected</TableHead>
                    <TableHead className="w-[120px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredFindings.map((finding) => {
                    const contextInfo = getContextDisplay(finding)
                    return (
                      <TableRow key={finding.id}>
                        <TableCell>
                          <Badge variant={getSeverityVariant(finding.severity)} className="flex items-center gap-1 w-fit">
                            {getSeverityIcon(finding.severity)}
                            <span>{finding.severity}</span>
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-sm">{finding.code}</TableCell>
                        <TableCell>{finding.message}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <span>{contextInfo.display}</span>
                            {contextInfo.hasExtra && (
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent side="left" className="max-w-xs">
                                  <div className="space-y-1">
                                    <p className="font-semibold text-xs">Additional Context:</p>
                                    {Object.entries(contextInfo.extra).map(([key, value]) => (
                                      <div key={key} className="text-xs">
                                        <span className="font-medium">{key}:</span>{' '}
                                        <span className="text-muted-foreground">
                                          {String(value)}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </TooltipContent>
                              </Tooltip>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm" onClick={() => handleViewInGraph(finding)}>
                            <ExternalLink className="h-4 w-4 mr-1" />
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </TooltipProvider>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
