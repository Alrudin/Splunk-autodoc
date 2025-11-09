import { useStore } from '@/store'
import { useDebounce } from '@/hooks/useDebounce'
import { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { X } from 'lucide-react'

interface FilterPanelProps {
  onFilterChange: () => void
}

export function FilterPanel({ onFilterChange }: FilterPanelProps) {
  const { filters, updateFilter, clearFilters } = useStore((state) => ({
    filters: state.filters,
    updateFilter: state.updateFilter,
    clearFilters: state.clearFilters,
  }))

  // Local state for text inputs (before debouncing)
  const [hostInput, setHostInput] = useState(filters.host || '')
  const [indexInput, setIndexInput] = useState(filters.index || '')
  const [appInput, setAppInput] = useState(filters.app || '')
  const [sourcetypeInput, setSourcetypeInput] = useState(filters.sourcetype || '')

  // Debounced values
  const debouncedHost = useDebounce(hostInput, 300)
  const debouncedIndex = useDebounce(indexInput, 300)
  const debouncedApp = useDebounce(appInput, 300)
  const debouncedSourcetype = useDebounce(sourcetypeInput, 300)

  // Update filters when debounced values change
  useEffect(() => {
    updateFilter('host', debouncedHost || undefined)
  }, [debouncedHost, updateFilter])

  useEffect(() => {
    updateFilter('index', debouncedIndex || undefined)
  }, [debouncedIndex, updateFilter])

  useEffect(() => {
    updateFilter('app', debouncedApp || undefined)
  }, [debouncedApp, updateFilter])

  useEffect(() => {
    updateFilter('sourcetype', debouncedSourcetype || undefined)
  }, [debouncedSourcetype, updateFilter])

  // Count active filters
  const activeFilterCount = Object.values(filters).filter(
    (v) => v !== undefined && v !== ''
  ).length

  const handleFilterChange = <K extends keyof typeof filters>(
    key: K,
    value: (typeof filters)[K]
  ) => {
    updateFilter(key, value)
    onFilterChange()
  }

  const handleClearFilters = () => {
    clearFilters()
    setHostInput('')
    setIndexInput('')
    setAppInput('')
    setSourcetypeInput('')
    onFilterChange()
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Filters</CardTitle>
          {activeFilterCount > 0 && (
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{activeFilterCount} active</Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearFilters}
                className="h-8 px-2"
              >
                <X className="h-4 w-4 mr-1" />
                Clear
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search Hosts */}
        <div className="space-y-2">
          <Label htmlFor="host-filter">Search Hosts</Label>
          <Input
            id="host-filter"
            placeholder="Filter by host ID..."
            value={hostInput}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setHostInput(e.target.value)}
          />
        </div>

        {/* Protocol Filter */}
        <div className="space-y-2">
          <Label htmlFor="protocol-filter">Protocol</Label>
          <Select
            value={filters.protocol || 'all'}
            onValueChange={(value: string) =>
              handleFilterChange('protocol', value === 'all' ? undefined : value)
            }
          >
            <SelectTrigger id="protocol-filter">
              <SelectValue placeholder="All protocols" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Protocols</SelectItem>
              <SelectItem value="splunktcp">Splunk TCP</SelectItem>
              <SelectItem value="http_event_collector">HTTP Event Collector</SelectItem>
              <SelectItem value="syslog">Syslog</SelectItem>
              <SelectItem value="tcp">TCP</SelectItem>
              <SelectItem value="udp">UDP</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Role Filter */}
        <div className="space-y-2">
          <Label htmlFor="role-filter">Host Role</Label>
          <Select
            value={filters.role || 'all'}
            onValueChange={(value: string) =>
              handleFilterChange('role', value === 'all' ? undefined : value)
            }
          >
            <SelectTrigger id="role-filter">
              <SelectValue placeholder="All roles" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Roles</SelectItem>
              <SelectItem value="universal_forwarder">Universal Forwarder</SelectItem>
              <SelectItem value="heavy_forwarder">Heavy Forwarder</SelectItem>
              <SelectItem value="indexer">Indexer</SelectItem>
              <SelectItem value="search_head">Search Head</SelectItem>
              <SelectItem value="unknown">Unknown</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* TLS Filter */}
        <div className="space-y-2">
          <Label htmlFor="tls-filter">TLS Status</Label>
          <Select
            value={
              filters.tls === undefined
                ? 'all'
                : filters.tls === true
                  ? 'enabled'
                  : 'disabled'
            }
            onValueChange={(value: string) => {
              if (value === 'all') {
                handleFilterChange('tls', undefined)
              } else {
                handleFilterChange('tls', value === 'enabled')
              }
            }}
          >
            <SelectTrigger id="tls-filter">
              <SelectValue placeholder="All" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="enabled">Enabled</SelectItem>
              <SelectItem value="disabled">Disabled</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Index Filter */}
        <div className="space-y-2">
          <Label htmlFor="index-filter">Index</Label>
          <Input
            id="index-filter"
            placeholder="Filter by index..."
            value={indexInput}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setIndexInput(e.target.value)}
          />
        </div>

        {/* App Filter */}
        <div className="space-y-2">
          <Label htmlFor="app-filter">App</Label>
          <Input
            id="app-filter"
            placeholder="Filter by app..."
            value={appInput}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAppInput(e.target.value)}
          />
        </div>

        {/* Sourcetype Filter */}
        <div className="space-y-2">
          <Label htmlFor="sourcetype-filter">Sourcetype</Label>
          <Input
            id="sourcetype-filter"
            placeholder="Filter by sourcetype..."
            value={sourcetypeInput}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSourcetypeInput(e.target.value)}
          />
        </div>

        {/* Active Filters Display */}
        {activeFilterCount > 0 && (
          <div className="space-y-2 pt-4 border-t">
            <Label className="text-sm text-muted-foreground">Active Filters:</Label>
            <div className="flex flex-wrap gap-2">
              {filters.host && (
                <Badge variant="outline" className="gap-1">
                  Host: {filters.host}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => handleFilterChange('host', undefined)}
                  />
                </Badge>
              )}
              {filters.protocol && (
                <Badge variant="outline" className="gap-1">
                  Protocol: {filters.protocol}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => handleFilterChange('protocol', undefined)}
                  />
                </Badge>
              )}
              {filters.role && (
                <Badge variant="outline" className="gap-1">
                  Role: {filters.role}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => handleFilterChange('role', undefined)}
                  />
                </Badge>
              )}
              {filters.tls !== undefined && (
                <Badge variant="outline" className="gap-1">
                  TLS: {filters.tls ? 'Enabled' : 'Disabled'}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => handleFilterChange('tls', undefined)}
                  />
                </Badge>
              )}
              {filters.index && (
                <Badge variant="outline" className="gap-1">
                  Index: {filters.index}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => handleFilterChange('index', undefined)}
                  />
                </Badge>
              )}
              {filters.app && (
                <Badge variant="outline" className="gap-1">
                  App: {filters.app}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => handleFilterChange('app', undefined)}
                  />
                </Badge>
              )}
              {filters.sourcetype && (
                <Badge variant="outline" className="gap-1">
                  Sourcetype: {filters.sourcetype}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => handleFilterChange('sourcetype', undefined)}
                  />
                </Badge>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
