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
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Autocomplete,
  Divider,
  FormHelperText
} from '@mui/material'
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material'
import { RootState } from '@/store/store'
import { fetchProjects, createProject } from '@/store/slices/projectSlice'

export const DashboardPage = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { projects, loading } = useSelector((state: RootState) => state.project)
  
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')
  
  // Category management state
  const [selectedCategories, setSelectedCategories] = useState<string[]>(['Person'])
  const [customCategory, setCustomCategory] = useState('')
  const [annotationFormat, setAnnotationFormat] = useState<string>('YOLO')
  
  // Predefined categories for common medical/general use cases
  const predefinedCategories = [
    'Person', 'Vehicle', 'Animal', 'Object', 
    'Anatomy', 'Lesion', 'Tool', 'Equipment',
    'Background', 'Artifact', 'Normal', 'Abnormal'
  ]

  useEffect(() => {
    dispatch(fetchProjects())
  }, [dispatch])

  // Category helper functions
  const handleAddCustomCategory = () => {
    if (customCategory.trim() && !selectedCategories.includes(customCategory.trim())) {
      setSelectedCategories([...selectedCategories, customCategory.trim()])
      setCustomCategory('')
    }
  }

  const handleRemoveCategory = (categoryToRemove: string) => {
    setSelectedCategories(selectedCategories.filter(cat => cat !== categoryToRemove))
  }

  const handleTogglePredefinedCategory = (category: string) => {
    if (selectedCategories.includes(category)) {
      handleRemoveCategory(category)
    } else {
      setSelectedCategories([...selectedCategories, category])
    }
  }

  const resetDialog = () => {
    setCreateDialogOpen(false)
    setNewProjectName('')
    setNewProjectDescription('')
    setSelectedCategories(['Person'])
    setCustomCategory('')
    setAnnotationFormat('YOLO')
  }

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return
    if (selectedCategories.length === 0) {
      alert('Please select at least one annotation category')
      return
    }
    
    try {
      const result = await dispatch(createProject({
        name: newProjectName,
        description: newProjectDescription,
        categories: selectedCategories,
        annotation_format: annotationFormat
      }))
      resetDialog()
      
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
      <Dialog open={createDialogOpen} onClose={resetDialog} maxWidth="md" fullWidth>
        <DialogTitle>Create New Project</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <Grid container spacing={3}>
            {/* Basic Project Info */}
            <Grid item xs={12}>
              <TextField
                autoFocus
                label="Project Name"
                fullWidth
                variant="outlined"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                sx={{ mb: 2 }}
              />
              <TextField
                label="Description (optional)"
                fullWidth
                multiline
                rows={3}
                variant="outlined"
                value={newProjectDescription}
                onChange={(e) => setNewProjectDescription(e.target.value)}
              />
            </Grid>

            {/* Annotation Format Selection */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>
                Annotation Format
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Choose the annotation format for your training data. This will determine how annotations are stored and exported.
              </Typography>
              
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Annotation Format</InputLabel>
                <Select
                  value={annotationFormat}
                  onChange={(e) => setAnnotationFormat(e.target.value)}
                  label="Annotation Format"
                >
                  <MenuItem value="YOLO">
                    <Box>
                      <Typography variant="body1" fontWeight="medium">YOLO</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Text files with normalized bounding boxes (center_x, center_y, width, height)
                      </Typography>
                    </Box>
                  </MenuItem>
                  <MenuItem value="COCO">
                    <Box>
                      <Typography variant="body1" fontWeight="medium">COCO</Typography>
                      <Typography variant="caption" color="text.secondary">
                        JSON format with segmentation polygons and detailed metadata
                      </Typography>
                    </Box>
                  </MenuItem>
                  <MenuItem value="PASCAL_VOC">
                    <Box>
                      <Typography variant="body1" fontWeight="medium">Pascal VOC</Typography>
                      <Typography variant="caption" color="text.secondary">
                        XML files with bounding box coordinates and object information
                      </Typography>
                    </Box>
                  </MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Category Selection */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Annotation Categories
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Select the categories you'll use for annotating objects in your videos. You can choose from predefined categories or add custom ones.
              </Typography>

              {/* Selected Categories */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Selected Categories ({selectedCategories.length}):
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {selectedCategories.map((category) => (
                    <Chip
                      key={category}
                      label={category}
                      onDelete={() => handleRemoveCategory(category)}
                      deleteIcon={<DeleteIcon />}
                      color="primary"
                      variant="outlined"
                    />
                  ))}
                  {selectedCategories.length === 0 && (
                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                      No categories selected
                    </Typography>
                  )}
                </Box>
              </Box>

              {/* Predefined Categories */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Predefined Categories:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {predefinedCategories.map((category) => (
                    <Chip
                      key={category}
                      label={category}
                      onClick={() => handleTogglePredefinedCategory(category)}
                      color={selectedCategories.includes(category) ? "primary" : "default"}
                      variant={selectedCategories.includes(category) ? "filled" : "outlined"}
                      sx={{ cursor: 'pointer' }}
                    />
                  ))}
                </Box>
              </Box>

              {/* Custom Category Input */}
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
                <TextField
                  label="Add Custom Category"
                  variant="outlined"
                  size="small"
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddCustomCategory()
                    }
                  }}
                  sx={{ flexGrow: 1 }}
                />
                <Button
                  variant="outlined"
                  onClick={handleAddCustomCategory}
                  disabled={!customCategory.trim()}
                  sx={{ height: 'fit-content' }}
                >
                  Add
                </Button>
              </Box>

              {selectedCategories.length === 0 && (
                <FormHelperText error sx={{ mt: 1 }}>
                  Please select at least one annotation category
                </FormHelperText>
              )}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={resetDialog}>Cancel</Button>
          <Button 
            onClick={handleCreateProject} 
            variant="contained"
            disabled={!newProjectName.trim() || selectedCategories.length === 0}
          >
            Create Project
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}