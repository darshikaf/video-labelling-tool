import React, { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { 
  Container, 
  Typography, 
  Grid, 
  Card, 
  CardContent, 
  Button, 
  Box,
  Paper,
  LinearProgress,
  Chip,
  IconButton
} from '@mui/material'
import { 
  CloudUpload, 
  PlayArrow, 
  VideoFile,
  Delete
} from '@mui/icons-material'
import { RootState } from '@/store/store'
import { fetchProject } from '@/store/slices/projectSlice'
import { fetchVideos, uploadVideo } from '@/store/slices/videoSlice'

export const ProjectPage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const { currentProject } = useSelector((state: RootState) => state.project)
  const { videos, loading } = useSelector((state: RootState) => state.video)
  
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)

  useEffect(() => {
    if (projectId) {
      dispatch(fetchProject(parseInt(projectId)))
      dispatch(fetchVideos(parseInt(projectId)))
    }
  }, [dispatch, projectId])

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !projectId) return

    // Validate file type
    const allowedTypes = [
      'video/mp4', 
      'video/avi', 
      'video/mov', 
      'video/quicktime',  // Standard QuickTime MIME type
      'video/x-quicktime', // Alternative QuickTime MIME type
      'video/mkv', 
      'video/x-matroska', // Alternative MKV MIME type
      'video/wmv',
      'video/x-ms-wmv'   // Alternative WMV MIME type
    ]
    
    // Also check file extension as fallback for QuickTime files
    const fileExtension = file.name.toLowerCase().split('.').pop()
    const allowedExtensions = ['mp4', 'avi', 'mov', 'qt', 'mkv', 'wmv']
    
    // Validate by MIME type or file extension (fallback for QuickTime)
    const isValidType = allowedTypes.includes(file.type) || allowedExtensions.includes(fileExtension || '')
    if (!isValidType) {
      alert('Please select a valid video file (MP4, AVI, MOV/QT, MKV, WMV)')
      return
    }

    // Validate file size (max 500MB)
    const maxSize = 500 * 1024 * 1024
    if (file.size > maxSize) {
      alert('File size must be less than 500MB')
      return
    }

    try {
      setUploadProgress(0)
      
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev === null) return 10
          if (prev >= 90) return prev
          return prev + 10
        })
      }, 200)

      await dispatch(uploadVideo({ projectId: parseInt(projectId), file }))
      
      clearInterval(progressInterval)
      setUploadProgress(100)
      
      setTimeout(() => {
        setUploadProgress(null)
      }, 1000)
      
      // Refresh video list
      dispatch(fetchVideos(parseInt(projectId)))
      
    } catch (error) {
      console.error('Upload failed:', error)
      setUploadProgress(null)
      alert('Upload failed. Please try again.')
    }
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 Bytes'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDuration = (duration: number | null) => {
    if (!duration) return 'Unknown'
    const minutes = Math.floor(duration / 60)
    const seconds = Math.floor(duration % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  if (!currentProject) {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography variant="h6" color="error">
          Project not found
        </Typography>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          {currentProject.name}
        </Typography>
        {currentProject.description && (
          <Typography variant="body1" color="text.secondary">
            {currentProject.description}
          </Typography>
        )}
      </Box>

      {/* Video Upload Area */}
      <Paper sx={{ p: 3, mb: 4, backgroundColor: 'grey.50' }}>
        <Typography variant="h6" gutterBottom>
          Upload Video
        </Typography>
        
        <Box
          sx={{
            border: '2px dashed',
            borderColor: 'grey.300',
            borderRadius: 2,
            p: 4,
            textAlign: 'center',
            cursor: 'pointer',
            '&:hover': {
              borderColor: 'primary.main',
              backgroundColor: 'action.hover'
            }
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Click to upload video
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Supported formats: MP4, AVI, MOV/QT (QuickTime), MKV, WMV (Max 500MB)
          </Typography>
          
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
        </Box>
        
        {uploadProgress !== null && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress variant="determinate" value={uploadProgress} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Uploading... {uploadProgress}%
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Video List */}
      <Typography variant="h5" gutterBottom>
        Videos ({videos.length})
      </Typography>
      
      <Grid container spacing={3}>
        {videos.map((video) => (
          <Grid item xs={12} sm={6} md={4} key={video.id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <VideoFile sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6" noWrap title={video.filename}>
                    {video.filename}
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  <Chip 
                    label={formatFileSize(video.file_size)} 
                    size="small" 
                    variant="outlined" 
                  />
                  <Chip 
                    label={formatDuration(video.duration)} 
                    size="small" 
                    variant="outlined" 
                  />
                  {video.width && video.height && (
                    <Chip 
                      label={`${video.width}x${video.height}`} 
                      size="small" 
                      variant="outlined" 
                    />
                  )}
                </Box>
                
                {video.fps && (
                  <Typography variant="body2" color="text.secondary">
                    {video.fps.toFixed(1)} FPS • {video.total_frames} frames
                  </Typography>
                )}
                
                <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                  Uploaded: {new Date(video.created_at).toLocaleDateString()}
                </Typography>
              </CardContent>
              
              <Box sx={{ p: 2, pt: 0 }}>
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={() => navigate(`/projects/${projectId}/videos/${video.id}/annotate`)}
                  fullWidth
                  sx={{ mb: 1 }}
                >
                  Start Annotation
                </Button>
                
                <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                  <IconButton 
                    size="small" 
                    color="error"
                    onClick={() => {
                      // TODO: Implement video deletion
                      console.log('Delete video:', video.id)
                    }}
                  >
                    <Delete />
                  </IconButton>
                </Box>
              </Box>
            </Card>
          </Grid>
        ))}
        
        {videos.length === 0 && (
          <Grid item xs={12}>
            <Box textAlign="center" py={6}>
              <VideoFile sx={{ fontSize: 64, color: 'grey.300', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No videos uploaded yet
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Upload your first video to start annotating
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Container>
  )
}