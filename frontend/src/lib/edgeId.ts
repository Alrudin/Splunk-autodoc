import type { Edge } from '@/types'

/**
 * Simple hash function for generating stable edge IDs
 */
function hashString(str: string): string {
  let hash = 0,
    index,
    character
  if (str.length === 0) return hash.toString()
  for (index = 0; index < str.length; index++) {
    chr = str.charCodeAt(i)
    // (hash << 5) - hash is equivalent to hash * 31; this bit-shifting operation helps distribute bits and reduce collisions, similar to the djb2 hash algorithm
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
