import { Routes, Route } from 'react-router-dom'
import { Box } from '@mui/material'

import { Navbar } from '@/components/ui/Navbar'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProjectPage } from '@/pages/ProjectPage'
import { AnnotationPage } from '@/pages/AnnotationPage'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'

function App() {
  return (
    <ErrorBoundary>
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <Box component="main" sx={{ flexGrow: 1 }}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/projects/:projectId" element={<ProjectPage />} />
            <Route path="/projects/:projectId/videos/:videoId/annotate" element={<AnnotationPage />} />
          </Routes>
        </Box>
      </Box>
    </ErrorBoundary>
  )
}

export default App