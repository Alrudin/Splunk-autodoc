import { useParams } from 'react-router-dom'

export function GraphExplorerPage() {
  const { graphId } = useParams<{ graphId: string }>()

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Graph Explorer</h1>
      <p className="text-muted-foreground mb-2">Graph ID: {graphId}</p>
      <p className="text-muted-foreground">
        Graph visualization will be implemented in the next phase.
      </p>
      <p className="text-muted-foreground mt-2">
        Features: Force-directed graph, hierarchical layout, filters, node/edge inspection,
        zoom/pan, exports.
      </p>
    </div>
  )
}
