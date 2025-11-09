import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import { useStore } from '@/store'
import type { Project, CreateProject, UpdateProject } from '@/types'

interface UseProjectsReturn {
  projects: Project[]
  isLoading: boolean
  error: string | null
  createProject: (data: CreateProject) => Promise<Project | null>
  deleteProject: (id: number) => Promise<boolean>
  updateProject: (id: number, data: UpdateProject) => Promise<Project | null>
  refetch: () => Promise<void>
}

export function useProjects(): UseProjectsReturn {
  const [projects, setProjectsState] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { setProjects } = useStore()

  const fetchProjects = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await api.getProjects()
      if (data) {
        setProjectsState(data)
        setProjects(data)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch projects'
      setError(errorMessage)
      console.error('Failed to fetch projects:', err)
    } finally {
      setIsLoading(false)
    }
  }, [setProjects])

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const createProject = async (data: CreateProject): Promise<Project | null> => {
    try {
      setError(null)
      const newProject = await api.createProject(data)
      if (newProject) {
        const updatedProjects = [...projects, newProject]
        setProjectsState(updatedProjects)
        setProjects(updatedProjects)
        return newProject
      }
      return null
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create project'
      setError(errorMessage)
      console.error('Failed to create project:', err)
      return null
    }
  }

  const deleteProject = async (id: number): Promise<boolean> => {
    try {
      setError(null)
      await api.deleteProject(id)
      const updatedProjects = projects.filter(p => p.id !== id)
      setProjectsState(updatedProjects)
      setProjects(updatedProjects)
      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete project'
      setError(errorMessage)
      console.error('Failed to delete project:', err)
      return false
    }
  }

  const updateProject = async (id: number, data: UpdateProject): Promise<Project | null> => {
    try {
      setError(null)
      const updatedProject = await api.updateProject(id, data)
      if (updatedProject) {
        const updatedProjects = projects.map(p => p.id === id ? updatedProject : p)
        setProjectsState(updatedProjects)
        setProjects(updatedProjects)
        return updatedProject
      }
      return null
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update project'
      setError(errorMessage)
      console.error('Failed to update project:', err)
      return null
    }
  }

  const refetch = async () => {
    await fetchProjects()
  }

  return {
    projects,
    isLoading,
    error,
    createProject,
    deleteProject,
    updateProject,
    refetch,
  }
}
