import { Box } from '@mui/material'
import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { Navbar } from '@/components/ui/Navbar'
import { AnnotationPage } from '@/pages/AnnotationPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { LoginPage } from '@/pages/LoginPage'
import { ProjectPage } from '@/pages/ProjectPage'
import { getCurrentUser } from '@/store/slices/authSlice'
import { RootState } from '@/store/store'

// Protected route wrapper - redirects to login if not authenticated
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useSelector((state: RootState) => state.auth)
  const location = useLocation()

  if (!token) {
    // Redirect to login, but save the attempted location
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

// Layout wrapper for authenticated pages (includes Navbar)
function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <Box component="main" sx={{ flexGrow: 1 }}>
        {children}
      </Box>
    </Box>
  )
}

function App() {
  const dispatch = useDispatch()
  const { token, user } = useSelector((state: RootState) => state.auth)

  // Fetch user info on app load if token exists but user is not loaded
  useEffect(() => {
    if (token && !user) {
      dispatch(getCurrentUser())
    }
  }, [token, user, dispatch])

  return (
    <ErrorBoundary>
      <Routes>
        {/* Public route - Login page (no navbar) */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes - require authentication */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <DashboardPage />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:projectId"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <ProjectPage />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:projectId/videos/:videoId/annotate"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout>
                <AnnotationPage />
              </AuthenticatedLayout>
            </ProtectedRoute>
          }
        />

        {/* Catch-all redirect to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
