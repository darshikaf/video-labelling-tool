import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { 
  Container, 
  Grid, 
  Paper, 
  Typography, 
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress
} from '@mui/material'
import { RootState } from '@/store/store'
import { fetchVideo, fetchFrame } from '@/store/slices/videoSlice'
import { setCurrentFrame } from '@/store/slices/videoSlice'
import { VideoPlayer } from '@/components/annotation/VideoPlayer'
import { AnnotationCanvas } from '@/components/annotation/AnnotationCanvas'
import { setPromptType, addPoint, addBox, setAwaitingDecision, runSAMPrediction, resetAnnotationState, clearPoints, clearBoxes, setCurrentMask } from '@/store/slices/annotationSlice'
import { annotationAPI } from '@/utils/api'

export const AnnotationPage = () => {
  const { projectId, videoId } = useParams<{ projectId: string; videoId: string }>()
  const dispatch = useDispatch()
  
  const { currentVideo, currentFrame, frameImageUrl, loading: videoLoading } = useSelector(
    (state: RootState) => state.video
  )
  const { 
    promptType, 
    selectedPoints, 
    selectedBoxes, 
    currentMask, 
    awaitingDecision,
    loading: annotationLoading 
  } = useSelector((state: RootState) => state.annotation)

  const [selectedCategory, setSelectedCategory] = useState('Person')
  const [categories] = useState(['Person', 'Vehicle', 'Animal', 'Object']) // Default categories
  const [samLoading, setSamLoading] = useState(false)
  const [editingMode, setEditingMode] = useState<'sam' | 'polygon'>('sam')
  const [polygonPoints, setPolygonPoints] = useState<any[]>([])

  useEffect(() => {
    if (videoId) {
      dispatch(fetchVideo(parseInt(videoId)))
    }
  }, [dispatch, videoId])

  useEffect(() => {
    if (currentVideo && videoId) {
      // Load first frame
      dispatch(fetchFrame({ videoId: parseInt(videoId), frameNumber: currentFrame }))
    }
  }, [dispatch, currentVideo, videoId, currentFrame])

  const handleFrameChange = (frameNumber: number) => {
    if (videoId && frameNumber !== currentFrame) {
      // Clear annotation state when changing frames
      dispatch(resetAnnotationState())
      dispatch(setCurrentFrame(frameNumber))
      dispatch(fetchFrame({ videoId: parseInt(videoId), frameNumber }))
    }
  }

  const handlePointClick = async (x: number, y: number, isPositive: boolean) => {
    console.log('DEBUG: AnnotationPage handlePointClick called with:', { x, y, isPositive })
    const newPoint = { x, y, is_positive: isPositive }
    console.log('DEBUG: Adding point to Redux state:', newPoint)
    dispatch(addPoint(newPoint))
    console.log('DEBUG: Running SAM prediction with updated points')
    await runPrediction([...selectedPoints, newPoint], selectedBoxes)
  }

  const handleBoxSelect = async (x1: number, y1: number, x2: number, y2: number) => {
    console.log('DEBUG: AnnotationPage handleBoxSelect called with:', { x1, y1, x2, y2 })
    const box = { x1, y1, x2, y2 }
    console.log('DEBUG: Adding box to Redux state:', box)
    dispatch(addBox(box))
    console.log('DEBUG: Running SAM prediction with updated boxes')
    await runPrediction(selectedPoints, [...selectedBoxes, box])
  }

  const runPrediction = async (points: any[], boxes: any[]) => {
    console.log('DEBUG: runPrediction called with:', { points, boxes, frameImageUrl, promptType })
    
    if (!frameImageUrl) {
      console.log('DEBUG: No frameImageUrl, returning early')
      return
    }

    try {
      console.log('DEBUG: Setting SAM loading to true')
      setSamLoading(true)
      
      // Convert image to base64
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      const img = new Image()
      
      img.onload = async () => {
        console.log('DEBUG: Image loaded, converting to base64')
        canvas.width = img.width
        canvas.height = img.height
        ctx?.drawImage(img, 0, 0)
        
        const imageData = canvas.toDataURL('image/jpeg').split(',')[1]
        console.log('DEBUG: Image converted to base64, length:', imageData.length)
        
        const request = {
          image_data: imageData,
          prompt_type: promptType,
          points: promptType === 'point' ? points : undefined,
          boxes: promptType === 'box' ? boxes : undefined
        }
        console.log('DEBUG: Dispatching SAM prediction with request:', request)

        await dispatch(runSAMPrediction(request))
        console.log('DEBUG: SAM prediction dispatch completed')
        setSamLoading(false)
      }
      
      img.onerror = (error) => {
        console.error('DEBUG: Image failed to load:', error)
        setSamLoading(false)
      }
      
      console.log('DEBUG: Setting image src:', frameImageUrl)
      img.src = frameImageUrl
    } catch (error) {
      console.error('DEBUG: SAM prediction failed:', error)
      setSamLoading(false)
    }
  }

  const handleSaveAnnotation = async () => {
    if (!currentMask || !videoId || !currentVideo) {
      console.error('Missing required data for saving annotation')
      return
    }

    try {
      console.log('Saving annotation:', {
        videoId,
        frameNumber: currentFrame,
        category: selectedCategory,
        maskLength: currentMask.length
      })

      await annotationAPI.createAnnotation(
        parseInt(videoId),
        currentFrame,
        selectedCategory,
        currentMask,
        selectedPoints,
        selectedBoxes,
        0.8 // Default confidence
      )

      console.log('Annotation saved successfully')
      dispatch(setAwaitingDecision(false))
      dispatch(resetAnnotationState())
      
    } catch (error) {
      console.error('Failed to save annotation:', error)
      // Could show error toast here
    }
  }

  const handleCancelAnnotation = () => {
    dispatch(setAwaitingDecision(false))
    dispatch(resetAnnotationState())
    setEditingMode('sam')
  }



  const handleEnterPolygonMode = () => {
    console.log('=== EDIT POLYGON BUTTON CLICKED ===')
    console.log('Current mask exists:', !!currentMask)
    console.log('Current mask length:', currentMask?.length)
    console.log('Current editing mode:', editingMode)
    
    if (currentMask) {
      console.log('Switching to polygon mode and converting mask...')
      setEditingMode('polygon')
      // Convert current mask to polygon points
      convertMaskToPolygon(currentMask)
    } else {
      console.log('No mask available for polygon editing')
    }
  }

  // Convert mask to polygon points (simplified version)
  const convertMaskToPolygon = (maskData: string) => {
    console.log('=== MASK TO POLYGON CONVERSION DEBUG ===')
    console.log('Input mask data length:', maskData.length)
    
    const img = new Image()
    img.onload = () => {
      console.log('Loaded mask image:', { width: img.width, height: img.height })
      
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)

      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data

      console.log('Canvas image data:', { 
        width: canvas.width, 
        height: canvas.height,
        dataLength: data.length 
      })

      // Sample some pixel values for debugging
      const samplePixels = []
      for (let i = 0; i < Math.min(20, data.length / 4); i++) {
        const idx = i * 4
        samplePixels.push({
          index: i,
          r: data[idx],
          g: data[idx + 1], 
          b: data[idx + 2],
          a: data[idx + 3]
        })
      }
      console.log('Sample pixels:', samplePixels)

      // Find bounding box
      let minX = canvas.width, maxX = 0, minY = canvas.height, maxY = 0
      let maskPixelCount = 0
      
      for (let y = 0; y < canvas.height; y++) {
        for (let x = 0; x < canvas.width; x++) {
          const idx = (y * canvas.width + x) * 4
          const value = data[idx] // R channel
          
          if (value > 128) {
            maskPixelCount++
            minX = Math.min(minX, x)
            maxX = Math.max(maxX, x)
            minY = Math.min(minY, y)
            maxY = Math.max(maxY, y)
          }
        }
      }

      console.log('Mask analysis result:', {
        maskPixelCount,
        boundingBox: { minX, minY, maxX, maxY },
        boundingBoxSize: { width: maxX - minX, height: maxY - minY }
      })

      if (maskPixelCount > 0) {
        console.log('Converting mask bounding box - using consistent 640x480 coordinate space')
        
        // FIXED APPROACH: Keep everything in 640x480 coordinate space for consistency
        // The mask is in 640x480 coordinate space (from SAM)
        // Keep polygon points in the SAME coordinate space (640x480)
        // This eliminates coordinate transformation conflicts
        
        console.log('Mask dimensions:', { width: canvas.width, height: canvas.height })
        console.log('Mask bounding box in 640x480 space:', { minX, minY, maxX, maxY })
        
        // Create polygon points directly from mask coordinates (no scaling)
        // Keep in 640x480 space, same as SAM system
        const points = [
          { x: Math.round(minX), y: Math.round(minY) },
          { x: Math.round(maxX), y: Math.round(minY) }, 
          { x: Math.round(maxX), y: Math.round(maxY) },
          { x: Math.round(minX), y: Math.round(maxY) }
        ]
        
        console.log('Created polygon points in 640x480 coordinate space:', {
          maskDimensions: { width: canvas.width, height: canvas.height },
          boundingBox: { minX, minY, maxX, maxY },
          polygonPoints: points,
          coordinateSpace: '640x480 (same as SAM)'
        })
        
        setPolygonPoints(points)
      } else {
        console.log('WARNING: No mask pixels found!')
      }
    }
    
    img.onerror = (error) => {
      console.error('Failed to load mask image:', error)
    }
    
    // Handle base64 data URL format
    if (maskData.startsWith('data:image')) {
      img.src = maskData
    } else {
      img.src = `data:image/png;base64,${maskData}`
    }
  }

  const handlePolygonChange = (points: any[]) => {
    setPolygonPoints(points)
  }

  const handleMaskGenerated = (maskData: string) => {
    // Update the current mask with the new polygon-generated mask
    dispatch(setCurrentMask(maskData))
    dispatch(setAwaitingDecision(true))
    console.log('New mask generated from polygon editing')
  }


  if (videoLoading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Container>
    )
  }

  if (!currentVideo) {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography variant="h6" color="error">
          Video not found
        </Typography>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 2 }}>
      <Typography variant="h4" gutterBottom>
        Annotating: {currentVideo.filename}
      </Typography>
      
      <Grid container spacing={3}>
        {/* Left Panel - Video Player */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Video Player
            </Typography>
            <VideoPlayer
              video={currentVideo}
              currentFrame={currentFrame}
              onFrameChange={handleFrameChange}
              frameImageUrl={frameImageUrl}
            />
          </Paper>
        </Grid>

        {/* Right Panel - Annotation Canvas or Polygon Editor */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              {editingMode === 'sam' ? 'Annotation Canvas' : 'Polygon Editor'}
            </Typography>
            
            {editingMode === 'polygon' && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Drag nodes • Click edges to add nodes • Shift+click nodes to delete
              </Typography>
            )}
            
            <AnnotationCanvas
              frameImageUrl={frameImageUrl}
              width={800}
              height={600}
              maxCanvasWidth={800}
              maxCanvasHeight={600}
              onPointClick={handlePointClick}
              onBoxSelect={handleBoxSelect}
              promptType={promptType}
              onPromptTypeChange={(type) => dispatch(setPromptType(type))}
              currentMask={currentMask}
              selectedPoints={selectedPoints}
              selectedBoxes={selectedBoxes}
              isPolygonMode={editingMode === 'polygon'}
              polygonPoints={polygonPoints}
              onPolygonChange={handlePolygonChange}
              onMaskGenerated={handleMaskGenerated}
            />
            
            {samLoading && editingMode === 'sam' && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                <CircularProgress size={24} />
                <Typography variant="body2" sx={{ ml: 1 }}>
                  Running SAM prediction...
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Bottom Panel - Annotation Controls */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Annotation Controls
            </Typography>
            
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={selectedCategory}
                    label="Category"
                    onChange={(e) => setSelectedCategory(e.target.value)}
                  >
                    {categories.map((category) => (
                      <MenuItem key={category} value={category}>
                        {category}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6} md={4}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip label={`Points: ${selectedPoints.length}`} size="small" />
                  <Chip label={`Boxes: ${selectedBoxes.length}`} size="small" />
                </Box>
              </Grid>
              
              <Grid item xs={12} md={5}>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {awaitingDecision ? (
                    <>
                      <Button 
                        variant="contained" 
                        color="primary" 
                        onClick={handleSaveAnnotation}
                      >
                        Save Annotation
                      </Button>
                      {editingMode === 'sam' && currentMask && (
                        <Button 
                          variant="outlined" 
                          color="secondary"
                          onClick={handleEnterPolygonMode}
                        >
                          Edit Polygon
                        </Button>
                      )}
                      <Button 
                        variant="outlined" 
                        onClick={handleCancelAnnotation}
                      >
                        Cancel
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button 
                        variant="outlined" 
                        onClick={() => {
                          // Clear current prompts and mask
                          dispatch(clearPoints())
                          dispatch(clearBoxes())
                          dispatch(resetAnnotationState())
                          setEditingMode('sam')
                        }}
                      >
                        Clear Prompts
                      </Button>
                      {editingMode === 'polygon' && (
                        <Button 
                          variant="outlined" 
                          onClick={() => setEditingMode('sam')}
                        >
                          Back to SAM
                        </Button>
                      )}
                    </>
                  )}
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

      </Grid>
    </Container>
  )
}