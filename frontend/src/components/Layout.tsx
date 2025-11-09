import { Outlet, NavLink } from 'react-router-dom'

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b">
        <nav className="container mx-auto px-4 py-4 flex items-center gap-6">
          <h1 className="text-xl font-bold">Splunk Event Flow Graph</h1>
          <NavLink
            to="/"
            className={({ isActive }) =>
              isActive ? 'font-semibold text-primary' : 'text-foreground hover:text-primary'
            }
          >
            Projects
          </NavLink>
          <NavLink
            to="/upload"
            className={({ isActive }) =>
              isActive ? 'font-semibold text-primary' : 'text-foreground hover:text-primary'
            }
          >
            Upload
          </NavLink>
        </nav>
      </header>
      <main className="flex-1 container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
