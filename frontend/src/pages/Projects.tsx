import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProjects } from '@/hooks/useProjects'
import { useStore } from '@/store'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { Plus, Trash2, FolderOpen, Loader2, Network, ExternalLink } from 'lucide-react'
import type { CreateProject, Project, Graph } from '@/types'

export function ProjectsPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { projects, isLoading, error, createProject, deleteProject } = useProjects()
  const { currentProject, setCurrentProject } = useStore()
  
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [projectLabels, setProjectLabels] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [expandedProjectId, setExpandedProjectId] = useState<number | null>(null)
  const [projectGraphs, setProjectGraphs] = useState<Record<number, Graph[]>>({})
  const [loadingGraphs, setLoadingGraphs] = useState<Record<number, boolean>>({})

  const handleCreateProject = async () => {
    if (!projectName.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Project name is required',
        variant: 'destructive',
      })
      return
    }

    setIsSubmitting(true)
    const labels = projectLabels
      .split(',')
      .map(label => label.trim())
      .filter(label => label.length > 0)

    const data: CreateProject = {
      name: projectName.trim(),
      labels: labels.length > 0 ? labels : undefined,
    }

    const newProject = await createProject(data)
    setIsSubmitting(false)

    if (newProject) {
      toast({
        title: 'Project created',
        description: `Project "${newProject.name}" has been created successfully.`,
      })
      setIsCreateDialogOpen(false)
      setProjectName('')
      setProjectLabels('')
    } else {
      toast({
        title: 'Error',
        description: 'Failed to create project. Please try again.',
        variant: 'destructive',
      })
    }
  }

  const handleDeleteProject = async () => {
    if (!selectedProjectId) return

    setIsSubmitting(true)
    const success = await deleteProject(selectedProjectId)
    setIsSubmitting(false)

    if (success) {
      // Clear currentProject if it matches the deleted project
      if (currentProject?.id === selectedProjectId) {
        setCurrentProject(null)
      }
      
      toast({
        title: 'Project deleted',
        description: 'Project has been deleted successfully.',
      })
      setIsDeleteDialogOpen(false)
      setSelectedProjectId(null)
    } else {
      toast({
        title: 'Error',
        description: 'Failed to delete project. Please try again.',
        variant: 'destructive',
      })
    }
  }

  const handleViewProject = (project: Project) => {
    setCurrentProject(project)
    navigate('/upload')
  }

  const handleViewGraphs = async (projectId: number) => {
    // Toggle expansion
    if (expandedProjectId === projectId) {
      setExpandedProjectId(null)
      return
    }

    setExpandedProjectId(projectId)

    // Load graphs if not already loaded
    if (!projectGraphs[projectId]) {
      setLoadingGraphs((prev) => ({ ...prev, [projectId]: true }))
      try {
        const graphs = await api.getProjectGraphs(projectId)
        setProjectGraphs((prev) => ({ ...prev, [projectId]: graphs || [] }))
      } catch (error) {
        toast({
          title: 'Error loading graphs',
          description: error instanceof Error ? error.message : 'Failed to load graphs',
          variant: 'destructive',
        })
        setProjectGraphs((prev) => ({ ...prev, [projectId]: [] }))
      } finally {
        setLoadingGraphs((prev) => ({ ...prev, [projectId]: false }))
      }
    }
  }

  const openDeleteDialog = (projectId: number) => {
    setSelectedProjectId(projectId)
    setIsDeleteDialogOpen(true)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Projects</h1>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Project
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading projects...</span>
        </div>
      ) : projects.length === 0 ? (
        <Alert>
          <AlertDescription>
            No projects yet. Create your first project to get started.
          </AlertDescription>
        </Alert>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Labels</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map((project) => [
                <TableRow key={project.id}>
                  <TableCell className="font-medium">{project.name}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {project.labels && project.labels.length > 0 ? (
                        project.labels.map((label, index) => (
                          <Badge key={index} variant="secondary">
                            {label}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-muted-foreground text-sm">No labels</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{formatDate(project.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewGraphs(project.id)}
                      >
                        <Network className="mr-2 h-4 w-4" />
                        {expandedProjectId === project.id ? 'Hide' : 'View'} Graphs
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewProject(project)}
                      >
                        <FolderOpen className="mr-2 h-4 w-4" />
                        Upload
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => openDeleteDialog(project.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>,

                expandedProjectId === project.id && (
                  <TableRow key={`expanded-${project.id}`}>
                    <TableCell colSpan={4} className="bg-muted/50">
                      <div className="py-4 px-2">
                        <h4 className="font-semibold mb-3 flex items-center gap-2">
                          <Network className="h-4 w-4" />
                          Graphs for {project.name}
                        </h4>
                        
                        {loadingGraphs[project.id] ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Loading graphs...
                          </div>
                        ) : projectGraphs[project.id] && projectGraphs[project.id].length > 0 ? (
                          <div className="space-y-2">
                            {projectGraphs[project.id].map((graph) => (
                              <div
                                key={graph.id}
                                className="flex items-center justify-between p-3 bg-background rounded-md border"
                              >
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">Graph #{graph.id}</span>
                                    <Badge variant="outline" className="text-xs">
                                      v{graph.version}
                                    </Badge>
                                  </div>
                                  <div className="text-sm text-muted-foreground">
                                    Created: {formatDate(graph.created_at)}
                                    {graph.json_blob?.meta && (
                                      <span className="ml-4">
                                        {graph.json_blob.meta.host_count || 0} hosts, {graph.json_blob.meta.edge_count || 0} edges
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <Button
                                  size="sm"
                                  onClick={() => navigate(`/graphs/${graph.id}`)}
                                >
                                  <ExternalLink className="mr-2 h-3 w-3" />
                                  View
                                </Button>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <Alert>
                            <AlertDescription>
                              No graphs yet. Upload a configuration file to generate a graph.
                            </AlertDescription>
                          </Alert>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              ])}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Create Project Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
            <DialogDescription>
              Create a new project to organize your Splunk configuration uploads and graphs.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="project-name">Project Name *</Label>
              <Input
                id="project-name"
                placeholder="My Splunk Project"
                value={projectName}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setProjectName(e.target.value)}
                onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter' && !isSubmitting) {
                    handleCreateProject()
                  }
                }}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="project-labels">Labels (optional)</Label>
              <Input
                id="project-labels"
                placeholder="production, us-east-1, team-alpha"
                value={projectLabels}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setProjectLabels(e.target.value)}
                onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter' && !isSubmitting) {
                    handleCreateProject()
                  }
                }}
              />
              <p className="text-sm text-muted-foreground">
                Comma-separated labels to categorize your project
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsCreateDialogOpen(false)
                setProjectName('')
                setProjectLabels('')
              }}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button onClick={handleCreateProject} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Project Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Project</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this project? This action cannot be undone.
              All associated uploads, jobs, and graphs will be permanently deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsDeleteDialogOpen(false)
                setSelectedProjectId(null)
              }}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteProject}
              disabled={isSubmitting}
            >
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete Project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

