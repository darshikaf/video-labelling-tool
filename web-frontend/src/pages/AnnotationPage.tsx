import { AnnotationCanvas } from '@/components/annotation/AnnotationCanvas'
import { SAM2Controls } from '@/components/annotation/SAM2Controls'
import { VideoPlayer } from '@/components/annotation/VideoPlayer'
import ExportDialog from '@/components/export/ExportDialog'
import { addBox, addPoint, clearBoxes, clearPoints, resetAnnotationState, runSAMPrediction, setAwaitingDecision, setCurrentMask, setPromptType } from '@/store/slices/annotationSlice'
import { addSAM2Object, setCurrentObjectId } from '@/store/slices/sam2Slice'
import { fetchFrame, fetchVideo, setCurrentFrame } from '@/store/slices/videoSlice'
import { AppDispatch, RootState } from '@/store/store'
import { PolygonPoint } from '@/types'
import { annotationAPI, projectAPI } from '@/utils/api'
import { FileDownload } from '@mui/icons-material'
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
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
  } = useSelector((state: RootState) => state.sam2)

  const [selectedCategory, setSelectedCategory] = useState('')
  const [categories, setCategories] = useState<Array<{ id: number, name: string, color: string }>>([])
  const [samLoading, setSamLoading] = useState(false)
  const [editingMode, setEditingMode] = useState<'sam' | 'polygon'>('sam')
  const [polygonPoints, setPolygonPoints] = useState<any[]>([])
  const [exportDialogOpen, setExportDialogOpen] = useState(false)
  const [existingAnnotations, setExistingAnnotations] = useState<any[]>([])
  const [selectedAnnotation, setSelectedAnnotation] = useState<any | null>(null) // For editing existing annotations
  const [editingAnnotationId, setEditingAnnotationId] = useState<number | null>(null) // Track which annotation we're editing

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
    const binaryMask = new Array(width * height).fill(0)
    let maskPixels = 0

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = (y * width + x) * 4
        if (data[idx] > 128) {
          binaryMask[y * width + x] = 1
          maskPixels++
        }
      }
    }

    console.log('Found', maskPixels, 'mask pixels')

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
        if (dist < nearestDist && dist <= 2) { // Only connect nearby pixels
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
              onPromptTypeChange={(type: 'point' | 'box') => dispatch(setPromptType(type))}
              currentMask={isSAM2Enabled ? null : currentMask}
              selectedPoints={isSAM2Enabled ? [] : selectedPoints}
              selectedBoxes={isSAM2Enabled ? [] : selectedBoxes}
              existingAnnotations={(() => {
                // In SAM 2 mode, show tracked object masks
                if (isSAM2Enabled && sam2FrameMasks[currentFrame]) {
                  const sam2MaskColors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'];
                  return Object.entries(sam2FrameMasks[currentFrame]).map(([objectIdStr, mask], index) => {
                    const objectId = parseInt(objectIdStr);
                    const obj = sam2Objects.find(o => o.object_id === objectId);
                    return {
                      mask: `data:image/png;base64,${mask}`,
                      category: obj?.category || 'SAM2 Object',
                      color: obj ? `rgb(${obj.color[0]},${obj.color[1]},${obj.color[2]})` : sam2MaskColors[index % sam2MaskColors.length],
                      annotationIndex: index,
                      annotationId: objectId,
                      isSelected: false
                    };
                  });
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

        {/* SAM 2 Controls Panel */}
        <Grid item xs={12}>
          <SAM2Controls
            videoPath={currentVideo?.file_path || ''}
            currentFrame={currentFrame}
            selectedCategory={selectedCategory}
            onObjectClick={(objectId) => dispatch(setCurrentObjectId(objectId))}
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
                    onChange={(e) => setSelectedCategory(e.target.value)}
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
                  {/* Show selected annotation controls */}
                  {selectedAnnotation ? (
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
