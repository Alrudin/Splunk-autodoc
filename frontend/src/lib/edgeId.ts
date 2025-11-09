import type { Edge } from '@/types'

/**
 * Simple hash function for generating stable edge IDs
 */
function hashString(str: string): string {
  let hash = 0,
    i,
    chr
  if (str.length === 0) return hash.toString()
  for (i = 0; i < str.length; i++) {
    chr = str.charCodeAt(i)
    hash = (hash << 5) - hash + chr
    hash |= 0 // Convert to 32bit integer
  }
  return Math.abs(hash).toString()
}

/**
 * Generate a robust unique edge ID using a hash of distinguishing properties.
 * This ensures consistent edge IDs across the application for the same edge.
 * 
 * @param edge - The edge object
 * @returns A unique string identifier for the edge
 */
export function edgeIdFromEdge(edge: Edge): string {
  const edgeComponents = [
    edge.src_host,
    edge.dst_host,
    edge.protocol,
    edge.indexes.slice().sort().join(','),
    edge.sourcetypes.slice().sort().join(','),
    String(edge.tls),
    String(edge.weight),
  ]
  return hashString(edgeComponents.join('|'))
}
