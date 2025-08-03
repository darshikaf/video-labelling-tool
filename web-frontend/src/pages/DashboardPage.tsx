import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { 
  Container, 
  Typography, 
  Grid, 
  Card, 
  CardContent, 
  Button, 
  Box, 
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  DialogActions,
  CircularProgress
} from '@mui/material'
import { Add as AddIcon } from '@mui/icons-material'
import { RootState } from '@/store/store'
import { fetchProjects, createProject } from '@/store/slices/projectSlice'

export const DashboardPage = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { projects, loading } = useSelector((state: RootState) => state.project)
  
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')

  useEffect(() => {
    dispatch(fetchProjects())
  }, [dispatch])

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return
    
    try {
      const result = await dispatch(createProject({
        name: newProjectName,
        description: newProjectDescription
      }))
      setCreateDialogOpen(false)
      setNewProjectName('')
      setNewProjectDescription('')
      
      // Navigate to the new project
      if (result.payload?.id) {
        navigate(`/projects/${result.payload.id}`)
      }
    } catch (error) {
      console.error('Failed to create project:', error)
    }
  }

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Container>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Video Annotation Projects
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          New Project
        </Button>
      </Box>

      <Grid container spacing={3}>
        {projects.map((project) => (
          <Grid item xs={12} sm={6} md={4} key={project.id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography gutterBottom variant="h5" component="h2">
                  {project.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {project.description || 'No description'}
                </Typography>
                <Typography variant="caption" display="block" sx={{ mt: 2 }}>
                  Created: {new Date(project.created_at).toLocaleDateString()}
                </Typography>
              </CardContent>
              <Box sx={{ p: 2, pt: 0 }}>
                <Button 
                  size="small" 
                  variant="outlined"
                  onClick={() => navigate(`/projects/${project.id}`)}
                  fullWidth
                >
                  Open Project
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
        
        {projects.length === 0 && (
          <Grid item xs={12}>
            <Box textAlign="center" py={6}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No projects yet. Create your first project to get started.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Projects help you organize your video annotation work.
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>

      {/* Create Project Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Project</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Project Name"
            fullWidth
            variant="outlined"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Description (optional)"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={newProjectDescription}
            onChange={(e) => setNewProjectDescription(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateProject} variant="contained">
            Create Project
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}