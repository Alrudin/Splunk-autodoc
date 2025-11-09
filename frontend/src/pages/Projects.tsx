import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProjects } from '@/hooks/useProjects'
import { useStore } from '@/store'
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
import { Plus, Trash2, FolderOpen, Loader2 } from 'lucide-react'
import type { CreateProject } from '@/types'

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

  const handleViewProject = (project: any) => {
    setCurrentProject(project)
    navigate('/upload')
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
              {projects.map((project) => (
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
                        onClick={() => handleViewProject(project)}
                      >
                        <FolderOpen className="mr-2 h-4 w-4" />
                        View
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
                </TableRow>
              ))}
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

