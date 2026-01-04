import { AnnotationCanvas } from '@/components/annotation/AnnotationCanvas'
import { SAM2Controls } from '@/components/annotation/SAM2Controls'
import { VideoPlayer } from '@/components/annotation/VideoPlayer'
import ExportDialog from '@/components/export/ExportDialog'
import { addBox, addPoint, clearBoxes, clearPoints, resetAnnotationState, runSAMPrediction, setAwaitingDecision, setCurrentMask, setPromptType } from '@/store/slices/annotationSlice'
import { addSAM2Object, fetchFrameMasks, refineSAM2Mask, setCurrentObjectId } from '@/store/slices/sam2Slice'
import { fetchFrame, fetchVideo, setCurrentFrame } from '@/store/slices/videoSlice'
import { AppDispatch, RootState } from '@/store/store'
import { PolygonPoint } from '@/types'
import { annotationAPI, projectAPI } from '@/utils/api'
import { Add, FileDownload } from '@mui/icons-material'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  ListItemIcon,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography
} from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useParams } from 'react-router-dom'

export const AnnotationPage = () => {
  const { projectId, videoId } = useParams<{ projectId: string; videoId: string }>()
  const dispatch = useDispatch<AppDispatch>()

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

  // SAM 2 state
  const {
    isEnabled: isSAM2Enabled,
    session: sam2Session,
    objects: sam2Objects,
    nextObjectId: sam2NextObjectId,
    frameMasks: sam2FrameMasks,
    sessionLoading: sam2Loading,
    isEditingBoundary: isSAM2EditingBoundary,
    editingObjectId: sam2EditingObjectId,
    editingFrameIdx: sam2EditingFrameIdx,
    isRefinementMode: isSAM2RefinementMode,
    currentObjectId: sam2CurrentObjectId,
  } = useSelector((state: RootState) => state.sam2)

  const [selectedCategory, setSelectedCategory] = useState('')
  const [categories, setCategories] = useState<Array<{ id: number, name: string, color: string }>>([])
  const [samLoading, setSamLoading] = useState(false)

  // Quick-add category state
  const [quickAddOpen, setQuickAddOpen] = useState(false)
  const [quickAddName, setQuickAddName] = useState('')
  const [quickAddLoading, setQuickAddLoading] = useState(false)
  const [editingMode, setEditingMode] = useState<'sam' | 'polygon'>('sam')
  const [polygonPoints, setPolygonPoints] = useState<any[]>([])
  const [exportDialogOpen, setExportDialogOpen] = useState(false)
  const [existingAnnotations, setExistingAnnotations] = useState<any[]>([])
  const [selectedAnnotation, setSelectedAnnotation] = useState<any | null>(null) // For editing existing annotations
  const [editingAnnotationId, setEditingAnnotationId] = useState<number | null>(null) // Track which annotation we're editing

  // SAM2 polygon editing state
  const [sam2PolygonPoints, setSam2PolygonPoints] = useState<any[]>([])
  const [sam2PolygonEditingMask, setSam2PolygonEditingMask] = useState<string | null>(null)

  // Debug effect to monitor polygon points
  useEffect(() => {
    console.log('SAM2: Polygon points updated', {
      count: sam2PolygonPoints.length,
      points: sam2PolygonPoints.slice(0, 3),
      isEditingBoundary: isSAM2EditingBoundary
    })
  }, [sam2PolygonPoints, isSAM2EditingBoundary])

  useEffect(() => {
    if (videoId) {
      dispatch(fetchVideo(parseInt(videoId)))
    }
  }, [dispatch, videoId])

  // Load initial frame only when video first loads (not on every currentFrame change)
  const initialFrameLoaded = useRef(false)
  useEffect(() => {
    if (currentVideo && videoId && !initialFrameLoaded.current) {
      // Load first frame only once when video is ready
      dispatch(fetchFrame({ videoId: parseInt(videoId), frameNumber: 0 }))
      initialFrameLoaded.current = true
    }
  }, [dispatch, currentVideo, videoId])

  // Fetch existing annotations when frame changes
  useEffect(() => {
    const fetchExistingAnnotations = async () => {
      if (videoId && currentFrame >= 0) {
        try {
          const annotations = await annotationAPI.getAnnotationsForFrame(
            parseInt(videoId),
            currentFrame
          )
          console.log('DEBUG: Fetched existing annotations:', annotations)
          setExistingAnnotations(annotations)
        } catch (error) {
          console.error('Failed to load existing annotations:', error)
          setExistingAnnotations([])
        }
      }
    }
    fetchExistingAnnotations()
  }, [videoId, currentFrame])

  // Fetch SAM2 frame masks on-demand when frame changes
  useEffect(() => {
    if (isSAM2Enabled && sam2Session && currentFrame >= 0) {
      // Only fetch if we don't already have masks for this frame
      if (!sam2FrameMasks[currentFrame]) {
        console.log(`SAM2: Fetching masks for frame ${currentFrame}`)
        dispatch(fetchFrameMasks({
          sessionId: sam2Session.session_id,
          frameIdx: currentFrame
        }))
      }
    }
  }, [dispatch, isSAM2Enabled, sam2Session, currentFrame, sam2FrameMasks])

  // Prefetch adjacent frames for smoother scrubbing (optional optimization)
  useEffect(() => {
    if (isSAM2Enabled && sam2Session && currentFrame >= 0 && currentVideo) {
      const totalFrames = currentVideo.total_frames || 0

      // Prefetch next 2-3 frames in the background (don't block UI)
      const framesToPrefetch = [
        currentFrame + 1,
        currentFrame + 2,
        currentFrame - 1, // Also prefetch previous frame
      ].filter(f => f >= 0 && f < totalFrames && !sam2FrameMasks[f])

      // Use setTimeout to defer prefetching (low priority)
      const timeoutId = setTimeout(() => {
        framesToPrefetch.forEach(frameIdx => {
          dispatch(fetchFrameMasks({
            sessionId: sam2Session.session_id,
            frameIdx
          }))
        })
      }, 100) // Wait 100ms before prefetching

      return () => clearTimeout(timeoutId)
    }
  }, [dispatch, isSAM2Enabled, sam2Session, currentFrame, currentVideo, sam2FrameMasks])

  // Load project categories
  useEffect(() => {
    const loadCategories = async () => {
      if (projectId) {
        try {
          const projectCategories = await projectAPI.getProjectCategories(parseInt(projectId))
          setCategories(projectCategories)
          // Set default category to first available category
          if (projectCategories.length > 0 && !selectedCategory) {
            setSelectedCategory(projectCategories[0].name)
          }
        } catch (error) {
          console.error('Failed to load project categories:', error)
          // Fallback to default categories
          const defaultCategories = [
            { id: 1, name: 'Person', color: '#FF6B6B' },
            { id: 2, name: 'Object', color: '#4ECDC4' }
          ]
          setCategories(defaultCategories)
          setSelectedCategory('Person')
        }
      }
    }
    loadCategories()
  }, [projectId, selectedCategory])

  // Handle SAM2 boundary editing mode activation
  useEffect(() => {
    console.log('SAM2 boundary editing effect triggered', {
      isSAM2EditingBoundary,
      sam2EditingObjectId,
      sam2EditingFrameIdx
    })

    if (isSAM2EditingBoundary && sam2EditingObjectId !== null && sam2EditingFrameIdx !== null) {
      // Get the mask for the object being edited
      const maskData = sam2FrameMasks[sam2EditingFrameIdx]?.[sam2EditingObjectId]
      console.log('SAM2: Checking for mask data', {
        frameIdx: sam2EditingFrameIdx,
        objectId: sam2EditingObjectId,
        hasMaskData: !!maskData,
        maskDataLength: maskData?.length
      })

      if (maskData) {
        console.log('SAM2: Starting boundary editing for object', sam2EditingObjectId, 'on frame', sam2EditingFrameIdx)
        setSam2PolygonEditingMask(maskData)
        // Convert mask to polygon using the same logic as original SAM
        convertSAM2MaskToPolygon(maskData)
      } else {
        console.error('SAM2: No mask data found for editing!')
      }
    } else {
      // Clear polygon editing state when not in boundary editing mode
      console.log('SAM2: Clearing polygon editing state')
      setSam2PolygonPoints([])
      setSam2PolygonEditingMask(null)
    }
  }, [isSAM2EditingBoundary, sam2EditingObjectId, sam2EditingFrameIdx, sam2FrameMasks])

  const handleFrameChange = (frameNumber: number) => {
    if (videoId && frameNumber !== currentFrame) {
      // Clear annotation state when changing frames
      dispatch(resetAnnotationState())
      setSelectedAnnotation(null) // Clear any selected annotation
      dispatch(setCurrentFrame(frameNumber))
      dispatch(fetchFrame({ videoId: parseInt(videoId), frameNumber }))
    }
  }

  const handlePointClick = async (x: number, y: number, isPositive: boolean) => {
    console.log('DEBUG: AnnotationPage handlePointClick called with:', { x, y, isPositive })

    // Handle SAM 2 mode
    if (isSAM2Enabled && sam2Session) {
      // If in refinement mode, refine the mask on the current frame
      if (isSAM2RefinementMode && sam2CurrentObjectId !== null) {
        console.log('SAM2: Refining mask for object', sam2CurrentObjectId, 'on frame', currentFrame)
        try {
          await dispatch(refineSAM2Mask({
            sessionId: sam2Session.session_id,
            frameIdx: currentFrame,
            objectId: sam2CurrentObjectId,
            points: [[x, y]],
            labels: [isPositive ? 1 : 0],
          })).unwrap()
          console.log('SAM2: Mask refined successfully')
        } catch (error) {
          console.error('SAM2: Failed to refine mask:', error)
          alert(`Failed to refine mask: ${error}`)
        }
        return
      }

      // Otherwise, add a new object
      console.log('SAM2: Adding object with point click')
      try {
        await dispatch(addSAM2Object({
          session_id: sam2Session.session_id,
          frame_idx: currentFrame,
          object_id: sam2NextObjectId,
          points: [[x, y]],
          labels: [isPositive ? 1 : 0],
          name: `${selectedCategory} ${sam2NextObjectId}`,
          category: selectedCategory,
        })).unwrap()
        console.log('SAM2: Object added successfully')
      } catch (error) {
        console.error('SAM2: Failed to add object:', error)
        alert(`Failed to add object: ${error}`)
      }
      return
    }

    // Original SAM (frame-by-frame) mode
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

  // Handle clicking on an existing annotation to select it for editing
  const handleAnnotationClick = (annotationId: number) => {
    console.log('DEBUG: Clicked on existing annotation:', annotationId)
    const annotation = existingAnnotations.find(ann => ann.id === annotationId)
    if (annotation) {
      setSelectedAnnotation(annotation)
      // Clear any in-progress new annotation
      dispatch(resetAnnotationState())
    }
  }

  // Handle deleting the selected annotation
  const handleDeleteSelectedAnnotation = async () => {
    if (selectedAnnotation && videoId) {
      try {
        await annotationAPI.deleteAnnotation(selectedAnnotation.id)
        setSelectedAnnotation(null)
        // Refresh annotations list
        const updatedAnnotations = await annotationAPI.getAnnotationsForFrame(
          parseInt(videoId),
          currentFrame
        )
        setExistingAnnotations(updatedAnnotations)
      } catch (error) {
        console.error('Failed to delete annotation:', error)
        alert('Failed to delete annotation')
      }
    }
  }

  // Clear selected annotation
  const handleClearSelection = () => {
    setSelectedAnnotation(null)
  }

  // Edit the selected annotation by converting its mask to polygon points
  const handleEditSelectedAnnotation = async () => {
    if (!selectedAnnotation) return

    try {
      // Fetch the mask image
      const maskUrl = selectedAnnotation.mask_url
      if (!maskUrl) {
        alert('No mask data available for this annotation')
        return
      }

      // Load the mask image and convert to polygon points
      const img = new Image()
      img.crossOrigin = 'anonymous'

      img.onload = () => {
        // Create canvas to read mask pixels
        const canvas = document.createElement('canvas')
        canvas.width = 640
        canvas.height = 480
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        ctx.drawImage(img, 0, 0, 640, 480)
        const imageData = ctx.getImageData(0, 0, 640, 480)
        const pixels = imageData.data

        // Find contour points from mask (simple edge detection)
        const points: Array<{ x: number; y: number }> = []
        const visited = new Set<string>()

        // Find edge pixels (where mask meets non-mask)
        for (let y = 1; y < 479; y += 3) { // Sample every 3 pixels for performance
          for (let x = 1; x < 639; x += 3) {
            const idx = (y * 640 + x) * 4
            const alpha = pixels[idx] // Using R channel for grayscale mask

            if (alpha > 128) { // This is a mask pixel
              // Check if it's an edge (has non-mask neighbor)
              const neighbors = [
                ((y - 1) * 640 + x) * 4,
                ((y + 1) * 640 + x) * 4,
                (y * 640 + (x - 1)) * 4,
                (y * 640 + (x + 1)) * 4,
              ]

              const isEdge = neighbors.some(nIdx => pixels[nIdx] <= 128)

              if (isEdge) {
                const key = `${x},${y}`
                if (!visited.has(key)) {
                  visited.add(key)
                  points.push({ x, y })
                }
              }
            }
          }
        }

        if (points.length < 3) {
          alert('Could not extract polygon from mask')
          return
        }

        // Sort points to form a proper polygon (convex hull approximation)
        const sortedPoints = sortPointsClockwise(points)

        // Simplify polygon (reduce number of points)
        const simplifiedPoints = simplifyPolygon(sortedPoints, 10)

        console.log('DEBUG: Converted mask to polygon with', simplifiedPoints.length, 'points')

        // Load polygon points and enter edit mode
        setPolygonPoints(simplifiedPoints)
        setEditingMode('polygon')
        setEditingAnnotationId(selectedAnnotation.id) // Track which annotation we're editing
        setSelectedAnnotation(null) // Clear selection since we're now editing

        // Set the mask as current mask for display during editing
        dispatch(setCurrentMask(null)) // Clear any existing mask
        dispatch(setAwaitingDecision(true)) // Show save/cancel controls
      }

      img.onerror = () => {
        alert('Failed to load mask image for editing')
      }

      img.src = maskUrl
    } catch (error) {
      console.error('Failed to edit annotation:', error)
      alert('Failed to edit annotation')
    }
  }

  // Sort points clockwise around centroid
  const sortPointsClockwise = (points: Array<{ x: number; y: number }>) => {
    const centroid = {
      x: points.reduce((sum, p) => sum + p.x, 0) / points.length,
      y: points.reduce((sum, p) => sum + p.y, 0) / points.length
    }

    return [...points].sort((a, b) => {
      const angleA = Math.atan2(a.y - centroid.y, a.x - centroid.x)
      const angleB = Math.atan2(b.y - centroid.y, b.x - centroid.x)
      return angleA - angleB
    })
  }

  // Simplify polygon using Douglas-Peucker-like algorithm
  const simplifyPolygon = (points: Array<{ x: number; y: number }>, tolerance: number) => {
    if (points.length <= 10) return points

    const result: Array<{ x: number; y: number }> = []
    const step = Math.max(1, Math.floor(points.length / 20)) // Keep ~20 points max

    for (let i = 0; i < points.length; i += step) {
      result.push(points[i])
    }

    // Ensure we have at least 3 points
    if (result.length < 3 && points.length >= 3) {
      return [points[0], points[Math.floor(points.length / 2)], points[points.length - 1]]
    }

    return result
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

  // Quick-add category handler
  const handleQuickAddCategory = async () => {
    if (!quickAddName.trim() || !projectId) {
      return
    }

    setQuickAddLoading(true)
    try {
      const newCategory = await projectAPI.createCategory(parseInt(projectId), quickAddName.trim())
      setCategories(prev => [...prev, newCategory])
      setSelectedCategory(newCategory.name)
      setQuickAddOpen(false)
      setQuickAddName('')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create category')
    } finally {
      setQuickAddLoading(false)
    }
  }

  const handleSaveAnnotation = async () => {
    if (!currentMask || !videoId || !currentVideo || !selectedCategory) {
      console.error('Missing required data for saving annotation')
      alert('Please ensure a category is selected and a mask is generated')
      return
    }

    try {
      // Find the category object to get additional metadata
      const categoryObj = categories.find(cat => cat.name === selectedCategory)

      console.log('Saving annotation with comprehensive metadata:', {
        projectId,
        videoId,
        videoName: currentVideo.filename,
        frameNumber: currentFrame,
        category: selectedCategory,
        categoryId: categoryObj?.id,
        categoryColor: categoryObj?.color,
        maskLength: currentMask.length,
        samPoints: selectedPoints,
        samBoxes: selectedBoxes,
        videoWidth: currentVideo.width,
        videoHeight: currentVideo.height,
        videoFps: currentVideo.fps,
        editingMode,
        isEditing: !!editingAnnotationId,
        timestamp: new Date().toISOString()
      })

      // If we're editing an existing annotation, delete the old one first
      if (editingAnnotationId) {
        try {
          await annotationAPI.deleteAnnotation(editingAnnotationId)
          console.log('Deleted old annotation before saving updated version:', editingAnnotationId)
        } catch (deleteError) {
          console.warn('Failed to delete old annotation, continuing with save:', deleteError)
        }
      }

      const savedAnnotation = await annotationAPI.createAnnotation(
        parseInt(videoId),
        currentFrame,
        selectedCategory,
        currentMask,
        selectedPoints,
        selectedBoxes,
        0.85 // Default confidence - can be enhanced with actual SAM confidence
      )

      console.log('Annotation saved successfully with full model training metadata', {
        annotationId: savedAnnotation.id,
        maskStorageKey: savedAnnotation.mask_storage_key || 'Not available',
        objectStorageEnabled: true,
        wasEdit: !!editingAnnotationId
      })
      dispatch(setAwaitingDecision(false))
      dispatch(resetAnnotationState())
      setEditingMode('sam') // Reset to SAM mode after saving
      setEditingAnnotationId(null) // Clear editing state
      setPolygonPoints([]) // Clear polygon points

      // Refresh existing annotations to show the newly saved one
      const updatedAnnotations = await annotationAPI.getAnnotationsForFrame(
        parseInt(videoId),
        currentFrame
      )
      setExistingAnnotations(updatedAnnotations)

    } catch (error) {
      console.error('Failed to save annotation:', error)
      alert('Failed to save annotation. Please try again.')
    }
  }

  const handleCancelAnnotation = () => {
    dispatch(setAwaitingDecision(false))
    dispatch(resetAnnotationState())
    setEditingMode('sam')
    setEditingAnnotationId(null) // Clear editing state
    setPolygonPoints([]) // Clear polygon points
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

  // Convert mask to polygon points - simplified for consistent 640x480 handling
  const convertMaskToPolygon = (maskData: string) => {
    console.log('=== MASK TO POLYGON CONVERSION (640x480 STANDARD) ===')
    console.log('Input mask data length:', maskData.length)

    const img = new Image()
    img.onload = () => {
      console.log('Loaded mask image:', { width: img.width, height: img.height })

      // ENFORCE: All masks should be 640x480 from SAM backend
      if (img.width !== 640 || img.height !== 480) {
        console.error(`Invalid mask dimensions: ${img.width}x${img.height}, expected 640x480`)
        console.error('This indicates a backend consistency issue. Proceeding with conversion but results may be misaligned.')
      }

      // Process mask directly since it should already be 640x480
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      canvas.width = 640
      canvas.height = 480
      ctx.drawImage(img, 0, 0, 640, 480) // Force to 640x480 if needed

      const imageData = ctx.getImageData(0, 0, 640, 480)
      const data = imageData.data

      console.log('Processing mask in standard 640x480 space:', {
        maskDimensions: { width: img.width, height: img.height },
        processingDimensions: { width: 640, height: 480 },
        dataLength: data.length
      })

      // Find bounding box and pixels
      let minX = 640, maxX = 0, minY = 480, maxY = 0
      let maskPixelCount = 0

      for (let y = 0; y < 480; y++) {
        for (let x = 0; x < 640; x++) {
          const idx = (y * 640 + x) * 4
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
        console.log('Tracing mask contour in 640x480 coordinate space')

        // Trace the contour of the mask to get actual boundary points
        const contourPoints = traceMaskContour(imageData, 640, 480)

        if (contourPoints.length > 0) {
          console.log('Traced contour with', contourPoints.length, 'points')

          // Simplify the contour to reduce number of points for better editing
          const simplifiedPoints = simplifyContour(contourPoints, 1.5)

          console.log('Simplified contour to', simplifiedPoints.length, 'points')

          console.log('Created polygon points from mask contour:', {
            coordinateSpace: '640x480 (SAM standard)',
            contourPoints: contourPoints.length,
            simplifiedPoints: simplifiedPoints.length,
            firstFewPoints: simplifiedPoints.slice(0, 5),
            boundingBox: {
              minX: Math.min(...simplifiedPoints.map(p => p.x)),
              minY: Math.min(...simplifiedPoints.map(p => p.y)),
              maxX: Math.max(...simplifiedPoints.map(p => p.x)),
              maxY: Math.max(...simplifiedPoints.map(p => p.y))
            }
          })

          setPolygonPoints(simplifiedPoints)
        } else {
          console.log('Contour tracing failed, falling back to bounding box')
          // Fallback to bounding box
          const points = [
            { x: minX, y: minY },
            { x: maxX, y: minY },
            { x: maxX, y: maxY },
            { x: minX, y: maxY }
          ]
          setPolygonPoints(points)
        }
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

  // Improved contour tracing using edge detection approach
  const traceMaskContour = (imageData: ImageData, width: number, height: number): PolygonPoint[] => {
    const data = imageData.data
    const contour: PolygonPoint[] = []

    console.log('Starting contour tracing on', width, 'x', height, 'image')

    // Create a binary mask for easier processing
    // Use threshold of 0 to catch all mask pixels
    const binaryMask = new Array(width * height).fill(0)
    let maskPixels = 0
    let minVal = 255, maxVal = 0
    let sampleVals = []

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = (y * width + x) * 4
        const pixelValue = data[idx]

        if (sampleVals.length < 10) sampleVals.push(pixelValue)

        if (pixelValue > 0) {  // Changed from 10 to 0 to catch all mask pixels
          binaryMask[y * width + x] = 1
          maskPixels++
          minVal = Math.min(minVal, pixelValue)
          maxVal = Math.max(maxVal, pixelValue)
        }
      }
    }

    console.log('traceMaskContour: Found', maskPixels, 'mask pixels with threshold 0')
    console.log('traceMaskContour: Pixel value range:', { min: minVal, max: maxVal, samples: sampleVals })

    if (maskPixels === 0) return []

    // Find the topmost, leftmost mask pixel for a consistent starting point
    let startX = -1, startY = -1
    for (let y = 0; y < height && startX === -1; y++) {
      for (let x = 0; x < width && startX === -1; x++) {
        if (binaryMask[y * width + x] === 1) {
          // Check if this is a boundary pixel (has at least one non-mask neighbor)
          let isBoundary = false
          for (let dy = -1; dy <= 1; dy++) {
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue
              const nx = x + dx
              const ny = y + dy
              if (nx < 0 || nx >= width || ny < 0 || ny >= height || binaryMask[ny * width + nx] === 0) {
                isBoundary = true
                break
              }
            }
            if (isBoundary) break
          }

          if (isBoundary) {
            startX = x
            startY = y
          }
        }
      }
    }

    if (startX === -1) return []

    console.log('Starting contour trace from:', startX, startY)

    // Use a more accurate boundary following algorithm
    // Find boundary pixels using edge detection
    const boundaryPixels: PolygonPoint[] = []

    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        if (binaryMask[y * width + x] === 1) {
          // Check if this pixel is on the boundary (has non-mask neighbors)
          let isBoundary = false
          const neighbors = [
            [-1, -1], [-1, 0], [-1, 1],
            [0, -1], [0, 1],
            [1, -1], [1, 0], [1, 1]
          ]

          for (const [dx, dy] of neighbors) {
            const nx = x + dx
            const ny = y + dy
            if (binaryMask[ny * width + nx] === 0) {
              isBoundary = true
              break
            }
          }

          if (isBoundary) {
            // Add slight offset to center the polygon on pixel boundaries
            // This helps with visual alignment precision
            boundaryPixels.push({ x: x + 0.5, y: y + 0.5 })
          }
        }
      }
    }

    console.log('Found', boundaryPixels.length, 'boundary pixels')

    if (boundaryPixels.length === 0) return []

    // Sort boundary pixels to create a proper contour
    // Start from the topmost, leftmost point
    boundaryPixels.sort((a, b) => {
      if (a.y !== b.y) return a.y - b.y
      return a.x - b.x
    })

    // Create ordered contour using nearest neighbor approach
    const orderedContour: PolygonPoint[] = []
    const used = new Set<string>()

    let current = boundaryPixels[0]
    orderedContour.push(current)
    used.add(`${current.x},${current.y}`)

    while (orderedContour.length < boundaryPixels.length) {
      let nearestDist = Infinity
      let nearest: PolygonPoint | null = null

      for (const pixel of boundaryPixels) {
        const key = `${pixel.x},${pixel.y}`
        if (used.has(key)) continue

        const dist = Math.sqrt((pixel.x - current.x) ** 2 + (pixel.y - current.y) ** 2)
        if (dist < nearestDist && dist <= 5) { // Connect pixels within reasonable distance
          nearestDist = dist
          nearest = pixel
        }
      }

      if (nearest) {
        orderedContour.push(nearest)
        used.add(`${nearest.x},${nearest.y}`)
        current = nearest
      } else {
        break // No more connected pixels
      }
    }

    console.log('Created ordered contour with', orderedContour.length, 'points')

    return orderedContour
  }

  // Simplify contour using Douglas-Peucker algorithm
  const simplifyContour = (points: PolygonPoint[], tolerance: number): PolygonPoint[] => {
    if (points.length <= 2) return points

    const douglasPeucker = (points: PolygonPoint[], epsilon: number): PolygonPoint[] => {
      if (points.length <= 2) return points

      // Find the point with maximum distance from line between first and last points
      let maxDistance = 0
      let maxIndex = 0
      const start = points[0]
      const end = points[points.length - 1]

      for (let i = 1; i < points.length - 1; i++) {
        const distance = pointToLineDistance(points[i], start, end)
        if (distance > maxDistance) {
          maxDistance = distance
          maxIndex = i
        }
      }

      // If max distance is greater than epsilon, recursively simplify
      if (maxDistance > epsilon) {
        const left = douglasPeucker(points.slice(0, maxIndex + 1), epsilon)
        const right = douglasPeucker(points.slice(maxIndex), epsilon)

        // Combine results (remove duplicate point at maxIndex)
        return [...left.slice(0, -1), ...right]
      } else {
        // Return simplified line
        return [start, end]
      }
    }

    return douglasPeucker(points, tolerance)
  }

  // Calculate perpendicular distance from point to line
  const pointToLineDistance = (point: PolygonPoint, lineStart: PolygonPoint, lineEnd: PolygonPoint): number => {
    const A = lineEnd.y - lineStart.y
    const B = lineStart.x - lineEnd.x
    const C = lineEnd.x * lineStart.y - lineStart.x * lineEnd.y

    return Math.abs(A * point.x + B * point.y + C) / Math.sqrt(A * A + B * B)
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

  // SAM2 polygon editing handlers
  const convertSAM2MaskToPolygon = (maskData: string) => {
    console.log('SAM2: Converting mask to polygon for boundary editing', { maskDataLength: maskData.length })
    // Reuse the existing mask-to-polygon conversion logic
    const img = new Image()
    img.onload = () => {
      console.log('SAM2: Mask image loaded:', { width: img.width, height: img.height })

      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        console.error('SAM2: Could not get canvas context')
        return
      }

      // IMPORTANT: Don't resize the mask - work with original dimensions
      // Then scale the polygon points to 640x480 later
      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)

      const imageData = ctx.getImageData(0, 0, img.width, img.height)

      // Check mask data - use lower threshold to handle antialiased edges
      const data = imageData.data
      let maskPixelCount = 0
      let minValue = 255, maxValue = 0
      let sampleValues = []
      for (let i = 0; i < data.length; i += 4) {
        const pixelValue = data[i]
        if (pixelValue > 0) {
          maskPixelCount++
          minValue = Math.min(minValue, pixelValue)
          maxValue = Math.max(maxValue, pixelValue)
        }
        if (sampleValues.length < 10) {
          sampleValues.push(pixelValue)
        }
      }
      console.log('SAM2: Mask pixel count:', maskPixelCount, 'dimensions:', img.width, 'x', img.height)
      console.log('SAM2: Pixel value range:', { min: minValue, max: maxValue, samples: sampleValues })

      // Trace contour using actual image dimensions
      const contourPoints = traceMaskContour(imageData, img.width, img.height)
      console.log('SAM2: Contour points found:', contourPoints.length)

      if (contourPoints.length > 0) {
        const simplifiedPoints = simplifyContour(contourPoints, 1.5)
        console.log('SAM2: Contour has', contourPoints.length, 'raw points')
        console.log('SAM2: Polygon created with', simplifiedPoints.length, 'simplified points', simplifiedPoints.slice(0, 5))

        // Scale polygon points from original dimensions to 640x480 for consistency
        const scaledPoints = simplifiedPoints.map(p => ({
          x: Math.round((p.x / img.width) * 640),
          y: Math.round((p.y / img.height) * 480)
        }))
        console.log('SAM2: Scaled polygon points to 640x480', scaledPoints.slice(0, 3))
        setSam2PolygonPoints(scaledPoints)
      } else {
        console.warn('SAM2: Could not trace contour, using bounding box')
        // Fallback to bounding box using actual image dimensions
        let minX = img.width, maxX = 0, minY = img.height, maxY = 0
        let foundMask = false
        for (let y = 0; y < img.height; y++) {
          for (let x = 0; x < img.width; x++) {
            const idx = (y * img.width + x) * 4
            if (data[idx] > 0) {  // Use threshold 0 instead of 128
              minX = Math.min(minX, x)
              maxX = Math.max(maxX, x)
              minY = Math.min(minY, y)
              maxY = Math.max(maxY, y)
              foundMask = true
            }
          }
        }

        if (foundMask) {
          // Scale bounding box to 640x480
          const points = [
            { x: Math.round((minX / img.width) * 640), y: Math.round((minY / img.height) * 480) },
            { x: Math.round((maxX / img.width) * 640), y: Math.round((minY / img.height) * 480) },
            { x: Math.round((maxX / img.width) * 640), y: Math.round((maxY / img.height) * 480) },
            { x: Math.round((minX / img.width) * 640), y: Math.round((maxY / img.height) * 480) }
          ]
          console.log('SAM2: Using scaled bounding box points:', points)
          setSam2PolygonPoints(points)
        } else {
          console.error('SAM2: No mask pixels found at all!')
        }
      }
    }

    img.onerror = (error) => {
      console.error('SAM2: Failed to load mask image:', error)
    }

    // Handle base64 data URL format
    if (maskData.startsWith('data:image')) {
      console.log('SAM2: Using data URL format')
      img.src = maskData
    } else {
      console.log('SAM2: Converting to data URL format')
      img.src = `data:image/png;base64,${maskData}`
    }
  }

  const handleSAM2PolygonChange = (points: any[]) => {
    setSam2PolygonPoints(points)
  }

  const handleSAM2MaskGenerated = (_maskData: string) => {
    // Don't auto-save - we'll save when "Done Editing" is clicked
    console.log('SAM2: Mask generated from polygon (will save when Done Editing is clicked)')
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
              {isSAM2EditingBoundary ? 'SAM2 Boundary Editor' : (editingMode === 'sam' ? 'Annotation Canvas' : 'Polygon Editor')}
            </Typography>

            {(editingMode === 'polygon' || isSAM2EditingBoundary) && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Drag nodes • Click edges to add nodes • Shift+click nodes to delete
              </Typography>
            )}

            {isSAM2RefinementMode && !isSAM2EditingBoundary && (
              <Alert severity="info" sx={{ mb: 1 }}>
                <Typography variant="body2">
                  <strong>Refinement Mode Active:</strong> Left-click to add positive points, right-click for negative points to refine masks.
                </Typography>
              </Alert>
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
              onPromptTypeChange={(type: 'point' | 'box') => dispatch(setPromptType(type))}
              currentMask={isSAM2Enabled ? null : currentMask}
              selectedPoints={isSAM2Enabled ? [] : selectedPoints}
              selectedBoxes={isSAM2Enabled ? [] : selectedBoxes}
              existingAnnotations={(() => {
                console.log('SAM2: Building existingAnnotations for canvas', {
                  isSAM2Enabled,
                  isSAM2EditingBoundary,
                  sam2EditingObjectId,
                  currentFrame,
                  hasMasks: !!sam2FrameMasks[currentFrame]
                })
                // In SAM 2 mode, show tracked object masks
                if (isSAM2Enabled && sam2FrameMasks[currentFrame]) {
                  const sam2MaskColors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'];
                  return Object.entries(sam2FrameMasks[currentFrame])
                    .map(([objectIdStr, mask], index) => {
                      const objectId = parseInt(objectIdStr);
                      const obj = sam2Objects.find(o => o.object_id === objectId);
                      // Don't show the mask being edited (will show polygon instead)
                      if (isSAM2EditingBoundary && objectId === sam2EditingObjectId) {
                        return null;
                      }
                      return {
                        mask: `data:image/png;base64,${mask}`,
                        category: obj?.category || 'SAM2 Object',
                        color: obj ? `rgb(${obj.color[0]},${obj.color[1]},${obj.color[2]})` : sam2MaskColors[index % sam2MaskColors.length],
                        annotationIndex: index,
                        annotationId: objectId,
                        isSelected: false
                      };
                    })
                    .filter((item): item is NonNullable<typeof item> => item !== null);
                }
                // Original mode: show existing annotations
                const mapped = existingAnnotations.map((ann: any, index: number) => ({
                  mask: ann.mask_url || '',
                  category: ann.category_name || 'Unknown',
                  color: ann.category_color || '#888888',
                  annotationIndex: index,
                  annotationId: ann.id,
                  isSelected: selectedAnnotation?.id === ann.id
                }))
                return mapped
              })()}
              onAnnotationClick={handleAnnotationClick}
              selectedAnnotationId={selectedAnnotation?.id}
              isPolygonMode={(() => {
                const mode = isSAM2EditingBoundary ? true : (editingMode === 'polygon')
                console.log('SAM2: AnnotationCanvas isPolygonMode', mode)
                return mode
              })()}
              polygonPoints={(() => {
                const points = isSAM2EditingBoundary ? sam2PolygonPoints : polygonPoints
                console.log('SAM2: AnnotationCanvas polygonPoints', {
                  isSAM2EditingBoundary,
                  pointsCount: points.length,
                  points: points.slice(0, 3)
                })
                return points
              })()}
              onPolygonChange={isSAM2EditingBoundary ? handleSAM2PolygonChange : handlePolygonChange}
              onMaskGenerated={isSAM2EditingBoundary ? handleSAM2MaskGenerated : handleMaskGenerated}
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

        {/* SAM 2 Controls Panel */}
        <Grid item xs={12}>
          <SAM2Controls
            videoPath={currentVideo?.file_path || ''}
            videoId={currentVideo?.id || 0}
            currentFrame={currentFrame}
            selectedCategory={selectedCategory}
            onObjectClick={(objectId) => dispatch(setCurrentObjectId(objectId))}
            sam2PolygonPoints={sam2PolygonPoints}
          />
        </Grid>

        {/* Bottom Panel - Annotation Controls */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              {isSAM2Enabled ? 'SAM 2 Video Annotation' : 'Annotation Controls'}
            </Typography>

            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={selectedCategory}
                    label="Category"
                    onChange={(e) => {
                      if (e.target.value === '__add_new__') {
                        setQuickAddOpen(true)
                      } else {
                        setSelectedCategory(e.target.value)
                      }
                    }}
                  >
                    {categories.map((category) => (
                      <MenuItem key={category.id} value={category.name}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box
                            sx={{
                              width: 12,
                              height: 12,
                              borderRadius: '50%',
                              backgroundColor: category.color
                            }}
                          />
                          {category.name}
                        </Box>
                      </MenuItem>
                    ))}
                    <Divider />
                    <MenuItem value="__add_new__">
                      <ListItemIcon>
                        <Add fontSize="small" />
                      </ListItemIcon>
                      Add New Category...
                    </MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} sm={6} md={2}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip label={`Points: ${selectedPoints.length}`} size="small" />
                  <Chip label={`Boxes: ${selectedBoxes.length}`} size="small" />
                </Box>
              </Grid>

              <Grid item xs={12} sm={6} md={2}>
                <Button
                  variant="outlined"
                  color="secondary"
                  size="small"
                  startIcon={<FileDownload />}
                  onClick={() => setExportDialogOpen(true)}
                  fullWidth
                >
                  Export
                </Button>
              </Grid>

              <Grid item xs={12} md={5}>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {/* Show nothing during SAM2 boundary editing - controls are in SAM2Controls panel */}
                  {isSAM2EditingBoundary ? null : selectedAnnotation ? (
                    <>
                      <Chip
                        label={`Selected: ${selectedAnnotation.category_name || 'Unknown'}`}
                        color="primary"
                        sx={{ mr: 1 }}
                      />
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={handleEditSelectedAnnotation}
                        size="small"
                      >
                        Edit Polygon
                      </Button>
                      <Button
                        variant="outlined"
                        color="error"
                        onClick={handleDeleteSelectedAnnotation}
                        size="small"
                      >
                        Delete
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={handleClearSelection}
                        size="small"
                      >
                        Deselect
                      </Button>
                    </>
                  ) : awaitingDecision ? (
                    <>
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={handleSaveAnnotation}
                      >
                        {editingAnnotationId ? 'Update Annotation' : 'Save Annotation'}
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

      {/* Quick Add Category Dialog */}
      <Dialog
        open={quickAddOpen}
        onClose={() => {
          setQuickAddOpen(false)
          setQuickAddName('')
        }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Add New Category</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Category Name"
            fullWidth
            variant="outlined"
            value={quickAddName}
            onChange={(e) => setQuickAddName(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleQuickAddCategory()}
            placeholder="e.g., Forceps, Liver, Scissors"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setQuickAddOpen(false)
            setQuickAddName('')
          }}>
            Cancel
          </Button>
          <Button
            onClick={handleQuickAddCategory}
            variant="contained"
            disabled={!quickAddName.trim() || quickAddLoading}
          >
            {quickAddLoading ? 'Adding...' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Export Dialog */}
      <ExportDialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        projectId={projectId ? parseInt(projectId) : 0}
        videoId={videoId ? parseInt(videoId) : undefined}
        projectName={currentVideo?.filename ? `Video_${currentVideo.filename}` : 'project'}
      />
    </Container>
  )
}
