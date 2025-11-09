import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'

const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        index: true,
        lazy: () => import('./pages/Projects').then((m) => ({ Component: m.ProjectsPage })),
      },
      {
        path: 'upload',
        lazy: () => import('./pages/Upload').then((m) => ({ Component: m.UploadPage })),
      },
      {
        path: 'graphs/:graphId',
        lazy: () =>
          import('./pages/GraphExplorer').then((m) => ({ Component: m.GraphExplorerPage })),
      },
      {
        path: 'graphs/:graphId/findings',
        lazy: () => import('./pages/Findings').then((m) => ({ Component: m.FindingsPage })),
      },
      {
        path: '*',
        lazy: () => import('./pages/NotFound').then((m) => ({ Component: m.NotFoundPage })),
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
