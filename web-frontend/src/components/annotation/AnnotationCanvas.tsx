import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { Box, Button, ButtonGroup, Typography, FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import { PolygonPoint } from '@/types'

/**
 * COORDINATE SYSTEM DOCUMENTATION:
 * 
 * This component uses a standardized 640x480 coordinate system for all annotation data:
 * - SAM points and boxes are stored in 640x480 coordinates
 * - Polygon points are stored in 640x480 coordinates
 * - The canvas display may have different dimensions, but all data is transformed
 *   from 640x480 to canvas coordinates for rendering
 * 
 * This ensures consistency across the entire annotation pipeline regardless of
 * the actual display size or original image dimensions.
 */

interface AnnotationCanvasProps {
  frameImageUrl: string | null
  width?: number
  height?: number
  onPointClick: (x: number, y: number, isPositive: boolean) => void
  onBoxSelect: (x1: number, y1: number, x2: number, y2: number) => void
  promptType: 'point' | 'box'
  onPromptTypeChange: (type: 'point' | 'box') => void
  currentMask: string | null
  selectedPoints?: Array<{x: number, y: number, is_positive: boolean}>
  selectedBoxes?: Array<{x1: number, y1: number, x2: number, y2: number}>
  existingAnnotations?: Array<{
    mask: string
    category: string
    color: string
  }>
  maxCanvasWidth?: number
  maxCanvasHeight?: number
  // Polygon editing props
  isPolygonMode?: boolean
  polygonPoints?: PolygonPoint[]
  onPolygonChange?: (points: PolygonPoint[]) => void
  onMaskGenerated?: (maskData: string) => void
}

export const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({
  frameImageUrl,
  width = 800,
  height = 600,
  maxCanvasWidth = 800,
  maxCanvasHeight = 600,
  onPointClick,
  onBoxSelect,
  promptType,
  onPromptTypeChange,
  currentMask,
  selectedPoints = [],
  selectedBoxes = [],
  existingAnnotations = [],
  isPolygonMode = false,
  polygonPoints = [],
  onPolygonChange,
  onMaskGenerated
}) => {
  console.log('DEBUG: AnnotationCanvas render with:', {
    frameImageUrl: frameImageUrl?.substring(0, 50),
    currentMask: currentMask?.substring(0, 50),
    selectedPoints: selectedPoints.length,
    selectedBoxes: selectedBoxes.length
  })
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null)
  const [isDrawingBox, setIsDrawingBox] = useState(false)
  const [boxStart, setBoxStart] = useState<{ x: number, y: number } | null>(null)
  const [pointMode, setPointMode] = useState<'positive' | 'negative'>('positive')
  
  // Polygon editing state
  const [selectedNode, setSelectedNode] = useState<number | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [hoveredNode, setHoveredNode] = useState<number | null>(null)
  const [hoveredEdge, setHoveredEdge] = useState<number | null>(null)
  
  // CRITICAL: Store image scaling information for coordinate transformation using ref to avoid re-renders
  const imageScalingRef = useRef<{
    originalWidth: number
    originalHeight: number
    drawWidth: number
    drawHeight: number
    offsetX: number
    offsetY: number
  } | null>(null)

  // Polygon editing constants and helper functions
  const NODE_RADIUS = 6
  const EDGE_DISTANCE_THRESHOLD = 10
  const EDGE_WIDTH = 2
  const NODE_SELECTED_RADIUS = 8

  // Helper function to transform coordinates from canvas to 640x480 SAM space
  const canvasToSAMCoords = useCallback((canvasX: number, canvasY: number) => {
    if (!imageScalingRef.current) return { x: canvasX, y: canvasY }
    
    const { drawWidth, drawHeight, offsetX, offsetY } = imageScalingRef.current
    
    // Remove offset and scale to 640x480 coordinates (same as SAM)
    const relativeX = (canvasX - offsetX) / drawWidth
    const relativeY = (canvasY - offsetY) / drawHeight
    
    return {
      x: Math.round(relativeX * 640),
      y: Math.round(relativeY * 480)
    }
  }, [])

  // Helper function to transform coordinates from 640x480 SAM space to canvas space
  const samToCanvasCoords = useCallback((samX: number, samY: number) => {
    if (!imageScalingRef.current) {
      console.warn('No image scaling info available, returning raw coordinates')
      return { x: samX, y: samY }
    }
    
    const { drawWidth, drawHeight, offsetX, offsetY } = imageScalingRef.current
    
    // Validate input coordinates are within expected SAM space
    if (samX < 0 || samX > 640 || samY < 0 || samY > 480) {
      console.warn('SAM coordinates out of expected 640x480 range:', { samX, samY })
    }
    
    // Convert from 640x480 SAM coordinates to canvas coordinates
    const relativeX = samX / 640
    const relativeY = samY / 480
    
    const canvasX = relativeX * drawWidth + offsetX
    const canvasY = relativeY * drawHeight + offsetY
    
    // Debug logging for coordinate transformation
    if (Math.random() < 0.1) { // Log 10% of transformations to avoid spam
      console.log('SAM to Canvas transformation:', {
        input: { samX, samY },
        relative: { relativeX, relativeY },
        canvas: { canvasX, canvasY },
        scaling: { drawWidth, drawHeight, offsetX, offsetY }
      })
    }
    
    return { x: canvasX, y: canvasY }
  }, [])

  // Helper function to transform coordinates from image to canvas space (legacy - keep for non-polygon features)
  const imageToCanvasCoords = useCallback((imageX: number, imageY: number) => {
    if (!imageScalingRef.current) return { x: imageX, y: imageY }
    
    const { drawWidth, drawHeight, offsetX, offsetY, originalWidth, originalHeight } = imageScalingRef.current
    
    // Scale from image to canvas coordinates and add offset
    const relativeX = imageX / originalWidth
    const relativeY = imageY / originalHeight
    
    return {
      x: relativeX * drawWidth + offsetX,
      y: relativeY * drawHeight + offsetY
    }
  }, [])

  // Calculate distance from point to line segment
  const pointToLineDistance = (
    px: number, py: number, 
    x1: number, y1: number, 
    x2: number, y2: number
  ): { distance: number; t: number } => {
    const dx = x2 - x1
    const dy = y2 - y1
    const lineLen2 = dx * dx + dy * dy

    if (lineLen2 === 0) {
      return { distance: Math.sqrt((px - x1) ** 2 + (py - y1) ** 2), t: 0 }
    }

    let t = ((px - x1) * dx + (py - y1) * dy) / lineLen2
    t = Math.max(0, Math.min(1, t))

    const projX = x1 + t * dx
    const projY = y1 + t * dy
    const distance = Math.sqrt((px - projX) ** 2 + (py - projY) ** 2)

    return { distance, t }
  }

  // Find nearest node in canvas coordinates (using SAM coordinate system)
  const findNearestNode = (canvasX: number, canvasY: number): number | null => {
    let minDist = Infinity
    let nearestNode = null

    polygonPoints.forEach((point, index) => {
      // Convert polygon point from 640x480 SAM space to canvas coordinates
      const canvasCoords = samToCanvasCoords(point.x, point.y)
      const dist = Math.sqrt((canvasX - canvasCoords.x) ** 2 + (canvasY - canvasCoords.y) ** 2)
      if (dist < minDist && dist <= NODE_RADIUS * 2) {
        minDist = dist
        nearestNode = index
      }
    })

    return nearestNode
  }

  // Find nearest edge in canvas coordinates (using SAM coordinate system)
  const findNearestEdge = (canvasX: number, canvasY: number): { index: number; t: number } | null => {
    let minDist = Infinity
    let nearestEdge = null

    for (let i = 0; i < polygonPoints.length; i++) {
      // Convert polygon points from 640x480 SAM space to canvas coordinates
      const p1 = samToCanvasCoords(polygonPoints[i].x, polygonPoints[i].y)
      const p2 = samToCanvasCoords(polygonPoints[(i + 1) % polygonPoints.length].x, polygonPoints[(i + 1) % polygonPoints.length].y)
      
      const { distance, t } = pointToLineDistance(canvasX, canvasY, p1.x, p1.y, p2.x, p2.y)
      
      if (distance < minDist && distance <= EDGE_DISTANCE_THRESHOLD) {
        minDist = distance
        nearestEdge = { index: i, t }
      }
    }

    return nearestEdge
  }

  const drawImage = useCallback(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx || !frameImageUrl) return

    const img = new Image()
    img.onload = () => {
      // Clear canvas
      ctx.clearRect(0, 0, width, height)
      
      // Calculate scaling to fit image in canvas while maintaining aspect ratio
      const imgAspectRatio = img.width / img.height
      const canvasAspectRatio = width / height
      
      let drawWidth = width
      let drawHeight = height
      let offsetX = 0
      let offsetY = 0
      
      if (imgAspectRatio > canvasAspectRatio) {
        drawHeight = width / imgAspectRatio
        offsetY = (height - drawHeight) / 2
      } else {
        drawWidth = height * imgAspectRatio
        offsetX = (width - drawWidth) / 2
      }
      
      // CRITICAL: Store scaling information for coordinate transformation
      imageScalingRef.current = {
        originalWidth: img.width,
        originalHeight: img.height,
        drawWidth,
        drawHeight,
        offsetX,
        offsetY
      }
      
      console.log('DEBUG: Image scaling info:', {
        original: `${img.width}x${img.height}`,
        displayed: `${drawWidth}x${drawHeight}`,
        offset: `(${offsetX}, ${offsetY})`,
        canvas: `${width}x${height}`
      })
      
      // Draw image
      ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight)
      
      // Only draw existing annotations on base canvas
      existingAnnotations.forEach((annotation, index) => {
        if (annotation.mask) {
          drawMaskOverlay(ctx, annotation.mask, annotation.color, 0.3)
        }
      })
      
      // Current mask will be drawn on overlay canvas, not here
    }
    img.src = frameImageUrl
  }, [frameImageUrl, width, height, existingAnnotations])

  const drawMaskOverlay = (ctx: CanvasRenderingContext2D, maskData: string, color: string, alpha: number) => {
    try {
      console.log('DEBUG: drawMaskOverlay called with:', { maskDataLength: maskData?.length, color, alpha })
      
      if (maskData) {
        // Create image from base64 mask data
        const maskImage = new Image()
        maskImage.onload = () => {
          console.log('DEBUG: Mask image loaded, dimensions:', { width: maskImage.width, height: maskImage.height })
          console.log('DEBUG: Expected image scaling info:', imageScalingRef.current)
          
          // Create a temporary canvas to process the mask
          const tempCanvas = document.createElement('canvas')
          const tempCtx = tempCanvas.getContext('2d')
          if (!tempCtx) {
            console.log('DEBUG: Failed to get temp canvas context')
            return
          }

          tempCanvas.width = maskImage.width
          tempCanvas.height = maskImage.height
          
          // Draw the mask image
          tempCtx.drawImage(maskImage, 0, 0)
          
          // Get image data to process pixel by pixel
          const imageData = tempCtx.getImageData(0, 0, maskImage.width, maskImage.height)
          const data = imageData.data
          
          console.log('DEBUG: Processing mask image data, total pixels:', data.length / 4)
          
          let maskPixelCount = 0
          let sampleValues = []
          // Convert grayscale mask to colored overlay
          for (let i = 0; i < data.length; i += 4) {
            const maskValue = data[i] // R channel (grayscale)
            
            // Sample first 10 pixel values for debugging
            if (sampleValues.length < 10) {
              sampleValues.push(maskValue)
            }
            
            if (maskValue > 128) { // If pixel is part of mask (white)
              maskPixelCount++
              // Parse color string (e.g., '#ff0000' -> RGB)
              const r = parseInt(color.substr(1, 2), 16)
              const g = parseInt(color.substr(3, 2), 16)
              const b = parseInt(color.substr(5, 2), 16)
              
              data[i] = r     // R
              data[i + 1] = g // G
              data[i + 2] = b // B
              data[i + 3] = Math.floor(alpha * 255) // Alpha
            } else {
              data[i + 3] = 0 // Transparent for non-mask areas
            }
          }
          
          console.log('DEBUG: Mask pixels found:', maskPixelCount)
          console.log('DEBUG: Sample pixel values:', sampleValues)
          
          if (maskPixelCount === 0) {
            console.log('DEBUG: WARNING - No mask pixels found with threshold 128! Trying with lower threshold...')
            
            // Try with threshold 0 (any non-zero pixel)
            let lowThresholdCount = 0
            for (let i = 0; i < data.length; i += 4) {
              const maskValue = data[i]
              if (maskValue > 0) {
                lowThresholdCount++
                // Parse color string (e.g., '#ff0000' -> RGB)
                const r = parseInt(color.substr(1, 2), 16)
                const g = parseInt(color.substr(3, 2), 16)
                const b = parseInt(color.substr(5, 2), 16)
                
                data[i] = r     // R
                data[i + 1] = g // G
                data[i + 2] = b // B
                data[i + 3] = Math.floor(alpha * 255) // Alpha
              } else {
                data[i + 3] = 0 // Transparent for non-mask areas
              }
            }
            
            console.log('DEBUG: Mask pixels found with threshold 0:', lowThresholdCount)
            maskPixelCount = lowThresholdCount
            
            if (maskPixelCount > 0) {
              tempCtx.putImageData(imageData, 0, 0)
            }
          } else {
            // Only update canvas if we found mask pixels with the high threshold
            tempCtx.putImageData(imageData, 0, 0)
          }
          
          // Draw the processed mask onto the main canvas
          // ENFORCED STANDARD: All masks must be 640x480 from SAM backend
          if (maskImage.width !== 640 || maskImage.height !== 480) {
            console.error(`Invalid mask dimensions: ${maskImage.width}x${maskImage.height}, expected 640x480. This indicates a backend issue.`)
            console.error('Mask will be displayed but may have alignment issues.')
          }
          
          if (imageScalingRef.current) {
            const { drawWidth, drawHeight, offsetX, offsetY } = imageScalingRef.current
            
            // Always scale from 640x480 SAM space to display area
            console.log('DEBUG: Drawing 640x480 mask scaled to display area:', {
              maskDimensions: { width: maskImage.width, height: maskImage.height },
              displayArea: { width: drawWidth, height: drawHeight, offsetX, offsetY }
            })
            ctx.drawImage(tempCanvas, offsetX, offsetY, drawWidth, drawHeight)
          } else {
            // Fallback to full canvas if no scaling info available
            console.warn('DEBUG: No image scaling info available, falling back to full canvas')
            ctx.drawImage(tempCanvas, 0, 0, width, height)
          }
          console.log('DEBUG: Mask overlay drawn to main canvas with', maskPixelCount, 'mask pixels')
        }
        
        maskImage.onerror = (error) => {
          console.error('DEBUG: Mask image failed to load:', error)
        }
        
        // Handle base64 data URL format
        if (maskData.startsWith('data:image')) {
          console.log('DEBUG: Using data URL format')
          maskImage.src = maskData
        } else {
          console.log('DEBUG: Converting to data URL format')
          maskImage.src = `data:image/png;base64,${maskData}`
        }
      } else {
        console.log('DEBUG: No mask data provided')
      }
    } catch (error) {
      console.error('DEBUG: Error drawing mask overlay:', error)
      // Fallback to simple indicator
      if (maskData) {
        ctx.globalAlpha = alpha
        ctx.fillStyle = color
        ctx.fillRect(width / 2 - 25, height / 2 - 25, 50, 50)
        ctx.globalAlpha = 1
      }
    }
  }

  const drawOverlay = useCallback(() => {
    const canvas = overlayCanvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    console.log('DEBUG: drawOverlay called, currentMask:', !!currentMask, 'points:', selectedPoints.length, 'boxes:', selectedBoxes.length)
    ctx.clearRect(0, 0, width, height)

    // Only draw current SAM mask on overlay (existing annotations are on base canvas)
    if (currentMask) {
      // Determine mask color based on the last positive point (or default to green)
      let maskColor = '#00ff00' // Default green for positive
      const lastPositivePoint = selectedPoints.slice().reverse().find(p => p.is_positive)
      const lastNegativePoint = selectedPoints.slice().reverse().find(p => !p.is_positive)
      
      // If we have both positive and negative points, use the most recent one's color
      if (lastNegativePoint && lastPositivePoint) {
        const lastNegativeIndex = selectedPoints.lastIndexOf(lastNegativePoint)
        const lastPositiveIndex = selectedPoints.lastIndexOf(lastPositivePoint)
        maskColor = lastNegativeIndex > lastPositiveIndex ? '#ff0000' : '#00ff00'
      } else if (lastNegativePoint && !lastPositivePoint) {
        maskColor = '#ff0000' // Red if only negative points
      }
      
      console.log('DEBUG: Drawing current mask in overlay with length:', currentMask.length, 'color:', maskColor)
      drawMaskOverlay(ctx, currentMask, maskColor, 0.6)
    }

    // Draw selected points (convert from 640x480 coordinates to canvas coordinates)
    selectedPoints.forEach((point) => {
      if (!imageScalingRef.current) return
      
      // Convert 640x480 coordinates back to canvas coordinates for display
      const canvasX = (point.x / 640) * imageScalingRef.current.drawWidth + imageScalingRef.current.offsetX
      const canvasY = (point.y / 480) * imageScalingRef.current.drawHeight + imageScalingRef.current.offsetY
      
      console.log('DEBUG: Rendering point at canvas coords:', { 
        stored640x480: { x: point.x, y: point.y }, 
        canvas: { x: canvasX, y: canvasY } 
      })
      
      ctx.beginPath()
      ctx.arc(canvasX, canvasY, 6, 0, 2 * Math.PI)
      ctx.fillStyle = point.is_positive ? '#00ff00' : '#ff0000'
      ctx.fill()
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 2
      ctx.stroke()
    })

    // Draw selected boxes (convert from 640x480 coordinates to canvas coordinates)
    selectedBoxes.forEach((box) => {
      if (!imageScalingRef.current) return
      
      // Convert 640x480 coordinates back to canvas coordinates for display
      const canvasX1 = (box.x1 / 640) * imageScalingRef.current.drawWidth + imageScalingRef.current.offsetX
      const canvasY1 = (box.y1 / 480) * imageScalingRef.current.drawHeight + imageScalingRef.current.offsetY
      const canvasX2 = (box.x2 / 640) * imageScalingRef.current.drawWidth + imageScalingRef.current.offsetX
      const canvasY2 = (box.y2 / 480) * imageScalingRef.current.drawHeight + imageScalingRef.current.offsetY
      
      ctx.strokeStyle = '#0088ff'
      ctx.lineWidth = 2
      ctx.setLineDash([])
      const boxWidth = Math.abs(canvasX2 - canvasX1)
      const boxHeight = Math.abs(canvasY2 - canvasY1)
      ctx.strokeRect(Math.min(canvasX1, canvasX2), Math.min(canvasY1, canvasY2), boxWidth, boxHeight)
    })

    // Draw box being drawn (convert from 640x480 coordinates to canvas coordinates)
    if (isDrawingBox && boxStart && imageScalingRef.current) {
      const canvasX = (boxStart.x / 640) * imageScalingRef.current.drawWidth + imageScalingRef.current.offsetX
      const canvasY = (boxStart.y / 480) * imageScalingRef.current.drawHeight + imageScalingRef.current.offsetY
      
      ctx.strokeStyle = '#ff0000'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 5])
      // This would be updated with current mouse position in a real implementation
      ctx.strokeRect(canvasX, canvasY, 100, 100)
      ctx.setLineDash([])
    }

    // Draw polygon in editing mode
    if (isPolygonMode && polygonPoints.length > 0) {
      // Validate polygon points are in expected coordinate space
      const outOfBoundsPoints = polygonPoints.filter(p => p.x < 0 || p.x > 640 || p.y < 0 || p.y > 480)
      if (outOfBoundsPoints.length > 0) {
        console.warn('Polygon points outside expected 640x480 range:', outOfBoundsPoints)
      }
      
      console.log('Drawing polygon in editing mode:', {
        polygonPointsCount: polygonPoints.length,
        coordinateSpace: '640x480 (SAM standard)',
        imageScaling: imageScalingRef.current,
        samplePoints: polygonPoints.slice(0, 3)
      })
      
      // Convert polygon points from 640x480 SAM space to canvas coordinates
      // This uses the exact same transformation as SAM points for consistency
      const canvasPoints = polygonPoints.map((point, index) => {
        const canvasCoords = samToCanvasCoords(point.x, point.y)
        
        // Log first few transformations for debugging
        if (index < 3) {
          console.log(`Polygon point ${index}: ${point.x},${point.y} (640x480) → ${canvasCoords.x.toFixed(1)},${canvasCoords.y.toFixed(1)} (canvas)`)
        }
        
        return canvasCoords
      })
      
      if (canvasPoints.length >= 2) {
        // Draw filled polygon background (semi-transparent)
        if (canvasPoints.length >= 3) {
          ctx.fillStyle = 'rgba(0, 255, 0, 0.2)'
          ctx.beginPath()
          ctx.moveTo(canvasPoints[0].x, canvasPoints[0].y)
          for (let i = 1; i < canvasPoints.length; i++) {
            ctx.lineTo(canvasPoints[i].x, canvasPoints[i].y)
          }
          ctx.closePath()
          ctx.fill()
        }

        // Draw edges
        canvasPoints.forEach((point, index) => {
          const nextIndex = (index + 1) % canvasPoints.length
          const nextPoint = canvasPoints[nextIndex]
          
          ctx.beginPath()
          ctx.moveTo(point.x, point.y)
          ctx.lineTo(nextPoint.x, nextPoint.y)
          
          // Highlight edges connected to selected/hovered nodes or hovered edge
          const isConnectedToSelected = (selectedNode === index || selectedNode === nextIndex)
          const isConnectedToHovered = (hoveredNode === index || hoveredNode === nextIndex)
          const isHoveredEdge = (hoveredEdge === index)
          
          if (isHoveredEdge) {
            ctx.strokeStyle = '#ffff00' // Yellow for hovered edge
            ctx.lineWidth = EDGE_WIDTH + 2
          } else if (isConnectedToSelected) {
            ctx.strokeStyle = '#ff6600' // Orange for edges connected to selected node
            ctx.lineWidth = EDGE_WIDTH + 1
          } else if (isConnectedToHovered) {
            ctx.strokeStyle = '#66ff66' // Light green for edges connected to hovered node
            ctx.lineWidth = EDGE_WIDTH + 1
          } else {
            ctx.strokeStyle = '#00ff00' // Green for normal edges
            ctx.lineWidth = EDGE_WIDTH
          }
          
          ctx.stroke()
        })

        // Draw nodes
        canvasPoints.forEach((point, index) => {
          const radius = (selectedNode === index || hoveredNode === index) ? NODE_SELECTED_RADIUS : NODE_RADIUS
          
          ctx.beginPath()
          ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI)
          
          // Fill color based on state
          if (selectedNode === index) {
            ctx.fillStyle = '#ff0000' // Red for selected
          } else if (hoveredNode === index) {
            ctx.fillStyle = '#ffaa00' // Orange for hovered
          } else {
            ctx.fillStyle = '#0066ff' // Blue for normal
          }
          
          ctx.fill()
          
          // White border
          ctx.strokeStyle = '#ffffff'
          ctx.lineWidth = 2
          ctx.stroke()
        })
      }
    }
  }, [isDrawingBox, boxStart, width, height, selectedPoints, selectedBoxes, currentMask, existingAnnotations, isPolygonMode, polygonPoints, selectedNode, hoveredNode, hoveredEdge])

  useEffect(() => {
    drawImage()
  }, [drawImage])

  useEffect(() => {
    drawOverlay()
  }, [drawOverlay])

  const handleCanvasMouseDown = (event: React.MouseEvent<HTMLCanvasElement>) => {
    console.log('DEBUG: Canvas mouse down at', { promptType, pointMode, isPolygonMode })
    
    const canvas = canvasRef.current
    if (!canvas) {
      console.log('DEBUG: No canvas reference found')
      return
    }

    if (!imageScalingRef.current) {
      console.log('DEBUG: No image scaling information available yet')
      return
    }

    const rect = canvas.getBoundingClientRect()
    const canvasX = event.clientX - rect.left
    const canvasY = event.clientY - rect.top
    console.log('DEBUG: Raw canvas coordinates:', { canvasX, canvasY })

    // Check if click is within the displayed image area
    if (canvasX < imageScalingRef.current.offsetX || 
        canvasX > imageScalingRef.current.offsetX + imageScalingRef.current.drawWidth ||
        canvasY < imageScalingRef.current.offsetY || 
        canvasY > imageScalingRef.current.offsetY + imageScalingRef.current.drawHeight) {
      console.log('DEBUG: Click outside image area, ignoring')
      return
    }

    // Handle polygon editing mode
    if (isPolygonMode) {
      // First check if clicking on a node
      const nearestNode = findNearestNode(canvasX, canvasY)
      if (nearestNode !== null) {
        // Handle node interaction
        if (event.shiftKey && polygonPoints.length > 3) {
          // Shift+click to delete node
          const newPoints = polygonPoints.filter((_, index) => index !== nearestNode)
          onPolygonChange?.(newPoints)
        } else {
          // Start dragging node
          setSelectedNode(nearestNode)
          setIsDragging(true)
        }
        return
      }

      // Check if clicking on an edge to add a new node
      const nearestEdge = findNearestEdge(canvasX, canvasY)
      if (nearestEdge && onPolygonChange) {
        const newPoints = [...polygonPoints]
        const p1 = newPoints[nearestEdge.index]
        const p2 = newPoints[(nearestEdge.index + 1) % newPoints.length]
        
        // Calculate the new point on the edge in SAM coordinate space
        const p1Sam = polygonPoints[nearestEdge.index]
        const p2Sam = polygonPoints[(nearestEdge.index + 1) % polygonPoints.length]
        
        // Interpolate in SAM coordinate space directly
        const newSamPoint = {
          x: Math.round(p1Sam.x + nearestEdge.t * (p2Sam.x - p1Sam.x)),
          y: Math.round(p1Sam.y + nearestEdge.t * (p2Sam.y - p1Sam.y))
        }
        
        newPoints.splice(nearestEdge.index + 1, 0, newSamPoint)
        onPolygonChange(newPoints)
      }
      return
    }

    // Convert to coordinates relative to displayed image (640x480 canvas space)
    const relativeX = canvasX - imageScalingRef.current.offsetX
    const relativeY = canvasY - imageScalingRef.current.offsetY

    // Scale to 640x480 coordinates (backend expects these exact dimensions)
    const scaledX = (relativeX / imageScalingRef.current.drawWidth) * 640
    const scaledY = (relativeY / imageScalingRef.current.drawHeight) * 480

    console.log('DEBUG: Coordinate transformation for 640x480 backend:', {
      canvas: { x: canvasX, y: canvasY },
      relative: { x: relativeX, y: relativeY },
      scaled640x480: { x: scaledX, y: scaledY }
    })

    if (promptType === 'point') {
      const isPositive = pointMode === 'positive'
      console.log('DEBUG: Calling onPointClick with 640x480 coordinates:', { x: scaledX, y: scaledY, isPositive })
      onPointClick(scaledX, scaledY, isPositive)
    } else if (promptType === 'box') {
      if (!isDrawingBox) {
        console.log('DEBUG: Starting box drawing')
        setIsDrawingBox(true)
        setBoxStart({ x: scaledX, y: scaledY })
      } else {
        console.log('DEBUG: Finishing box drawing')
        if (boxStart) {
          console.log('DEBUG: Calling onBoxSelect with 640x480 coordinates:', { 
            x1: boxStart.x, y1: boxStart.y, x2: scaledX, y2: scaledY 
          })
          onBoxSelect(boxStart.x, boxStart.y, scaledX, scaledY)
          setIsDrawingBox(false)
          setBoxStart(null)
        }
      }
    }
  }

  const handleCanvasMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isPolygonMode) return
    
    const canvas = canvasRef.current
    if (!canvas || !imageScalingRef.current) return

    const rect = canvas.getBoundingClientRect()
    const canvasX = event.clientX - rect.left
    const canvasY = event.clientY - rect.top

    // Check if within image area
    if (canvasX < imageScalingRef.current.offsetX || 
        canvasX > imageScalingRef.current.offsetX + imageScalingRef.current.drawWidth ||
        canvasY < imageScalingRef.current.offsetY || 
        canvasY > imageScalingRef.current.offsetY + imageScalingRef.current.drawHeight) {
      return
    }

    if (isDragging && selectedNode !== null && onPolygonChange) {
      // Update node position while dragging in SAM coordinate space
      const newPoints = [...polygonPoints]
      const samCoords = canvasToSAMCoords(canvasX, canvasY)
      newPoints[selectedNode] = samCoords
      onPolygonChange(newPoints)
    } else {
      // Update hover states for visual feedback
      const nearestNode = findNearestNode(canvasX, canvasY)
      const nearestEdge = nearestNode === null ? findNearestEdge(canvasX, canvasY) : null
      
      setHoveredNode(nearestNode)
      setHoveredEdge(nearestEdge?.index ?? null)
      
      // Update cursor based on what's being hovered
      if (nearestNode !== null) {
        canvas.style.cursor = 'move'
      } else if (nearestEdge) {
        canvas.style.cursor = 'crosshair'
      } else {
        canvas.style.cursor = 'default'
      }
    }
  }

  const handleCanvasMouseUp = () => {
    if (isPolygonMode) {
      setIsDragging(false)
      setSelectedNode(null)
    }
  }

  // Convert polygon points to mask
  const polygonToMask = useCallback((points: PolygonPoint[]): string => {
    if (points.length < 3) return ''

    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (!ctx) return ''

    canvas.width = 640  // Standard processing size
    canvas.height = 480

    // Draw filled polygon
    ctx.fillStyle = 'black'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = 'white'
    
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y)
    }
    ctx.closePath()
    ctx.fill()

    // Convert to base64
    return canvas.toDataURL().split(',')[1]
  }, [])

  // Auto-generate mask when polygon changes in edit mode
  useEffect(() => {
    if (isPolygonMode && polygonPoints.length >= 3 && onMaskGenerated) {
      const maskData = polygonToMask(polygonPoints)
      if (maskData) {
        onMaskGenerated(maskData)
      }
    }
  }, [isPolygonMode, polygonPoints, onMaskGenerated, polygonToMask])

  return (
    <Box>
      {/* Tool Selection */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <FormControl size="small">
          <InputLabel>Tool</InputLabel>
          <Select
            value={promptType}
            label="Tool"
            onChange={(e) => onPromptTypeChange(e.target.value as 'point' | 'box')}
          >
            <MenuItem value="point">Point</MenuItem>
            <MenuItem value="box">Box</MenuItem>
          </Select>
        </FormControl>

        {promptType === 'point' && (
          <ButtonGroup size="small">
            <Button
              variant={pointMode === 'positive' ? 'contained' : 'outlined'}
              onClick={() => setPointMode('positive')}
              color="success"
            >
              Positive
            </Button>
            <Button
              variant={pointMode === 'negative' ? 'contained' : 'outlined'}
              onClick={() => setPointMode('negative')}
              color="error"
            >
              Negative
            </Button>
          </ButtonGroup>
        )}
      </Box>

      {/* Canvas Container */}
      <Box
        sx={{
          position: 'relative',
          width,
          height,
          border: '1px solid #ccc',
          cursor: promptType === 'point' ? 'crosshair' : isDrawingBox ? 'crosshair' : 'crosshair'
        }}
      >
        {/* Base canvas for image and annotations */}
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseUp}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            zIndex: 1
          }}
        />
        
        {/* Overlay canvas for temporary drawings */}
        <canvas
          ref={overlayCanvasRef}
          width={width}
          height={height}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            zIndex: 2,
            pointerEvents: 'none'
          }}
        />

        {!frameImageUrl && (
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: 'text.secondary',
              zIndex: 3
            }}
          >
            <Typography>No frame selected</Typography>
          </Box>
        )}
      </Box>

      {/* Instructions */}
      <Box sx={{ mt: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {promptType === 'point' 
            ? `Click on the image to add ${pointMode} points for SAM segmentation`
            : isDrawingBox 
              ? 'Click to finish drawing the bounding box'
              : 'Click and drag to draw a bounding box for SAM segmentation'
          }
        </Typography>
      </Box>
    </Box>
  )
}