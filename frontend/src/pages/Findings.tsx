import { useParams } from 'react-router-dom'

export function FindingsPage() {
  const { graphId } = useParams<{ graphId: string }>()

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Findings</h1>
      <p className="text-muted-foreground mb-2">Graph ID: {graphId}</p>
      <p className="text-muted-foreground">
        Findings table will be implemented in the next phase.
      </p>
      <p className="text-muted-foreground mt-2">
        Features: Display findings with severity/code/message, filter by severity and code, link to
        affected nodes/edges.
      </p>
    </div>
  )
}
