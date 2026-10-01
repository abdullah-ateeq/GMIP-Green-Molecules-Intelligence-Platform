import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { Companies } from './pages/Companies'
import { CompanyDetail } from './pages/CompanyDetail'
import { Dashboard } from './pages/Dashboard'
import { ProjectDetail } from './pages/ProjectDetail'
import { Projects } from './pages/Projects'
import { Sources } from './pages/Sources'

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/companies" element={<Companies />} />
          <Route path="/companies/:entityId" element={<CompanyDetail />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:entityId" element={<ProjectDetail />} />
          <Route path="/sources" element={<Sources />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}

export default App
