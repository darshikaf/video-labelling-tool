import React, { useRef, useEffect, useState, useCallback } from 'react'
import { Box, Button, ButtonGroup, Typography } from '@mui/material'
import { PolygonPoint } from '@/types'

interface PolygonEditorProps {
  maskData: string | null
  onPolygonChange: (points: PolygonPoint[]) => void
  onMaskGenerated: (maskData: string) => void
  width?: number
  height?: number
}

export const PolygonEditor: React.FC<PolygonEditorProps> = ({
  maskData,
  onPolygonChange,
  onMaskGenerated,
  width = 800,
  height = 600
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [polygonPoints, setPolygonPoints] = useState<PolygonPoint[]>([])
  const [selectedNode, setSelectedNode] = useState<number | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [hoveredNode, setHoveredNode] = useState<number | null>(null)
  const [hoveredEdge, setHoveredEdge] = useState<number | null>(null)

  const NODE_RADIUS = 6
  const EDGE_DISTANCE_THRESHOLD = 10
  const EDGE_WIDTH = 2
  const NODE_SELECTED_RADIUS = 8

  // Convert mask to polygon points
  const maskToPolygon = useCallback((mask: string): PolygonPoint[] => {
    if (!mask) return []

    try {
      // Create image from base64 mask data
      const img = new Image()
      return new Promise<PolygonPoint[]>((resolve) => {
        img.onload = () => {
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')
          if (!ctx) {
            resolve([])
            return
          }

          canvas.width = img.width
          canvas.height = img.height
          ctx.drawImage(img, 0, 0)

          // Get image data
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
          const data = imageData.data

          // Create binary mask
          const binaryMask: number[][] = []
          for (let y = 0; y < canvas.height; y++) {
            binaryMask[y] = []
            for (let x = 0; x < canvas.width; x++) {
              const idx = (y * canvas.width + x) * 4
              const value = data[idx] // R channel
              binaryMask[y][x] = value > 128 ? 1 : 0
            }
          }

          // Find contour using a simple edge tracing algorithm
          const points = findContourPoints(binaryMask)
          resolve(points)
        }

        img.onerror = () => resolve([])
        
        // Handle base64 data URL format
        if (mask.startsWith('data:image')) {
          img.src = mask
        } else {
          img.src = `data:image/png;base64,${mask}`
        }
      })
    } catch (error) {
      console.error('Error converting mask to polygon:', error)
      return []
    }
  }, [])

  // Simple contour finding algorithm
  const findContourPoints = (binaryMask: number[][]): PolygonPoint[] => {
    const height = binaryMask.length
    const width = binaryMask[0]?.length || 0
    
    if (height === 0 || width === 0) return []

    // Find first edge point
    let startX = -1, startY = -1
    outer: for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (binaryMask[y][x] === 1) {
          // Check if it's an edge point (has at least one non-mask neighbor)
          const neighbors = [
            [x-1, y], [x+1, y], [x, y-1], [x, y+1]
          ]
          for (const [nx, ny] of neighbors) {
            if (nx < 0 || nx >= width || ny < 0 || ny >= height || binaryMask[ny][nx] === 0) {
              startX = x
              startY = y
              break outer
            }
          }
        }
      }
    }

    if (startX === -1) return []

    // Simplified: just create a rectangle approximation for now
    // In a real implementation, you'd use proper contour tracing
    const points: PolygonPoint[] = []
    
    // Find bounding box
    let minX = width, maxX = 0, minY = height, maxY = 0
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (binaryMask[y][x] === 1) {
          minX = Math.min(minX, x)
          maxX = Math.max(maxX, x)
          minY = Math.min(minY, y)
          maxY = Math.max(maxY, y)
        }
      }
    }

    // Create polygon points from bounding box (simplified)
    points.push({ x: minX, y: minY })
    points.push({ x: maxX, y: minY })
    points.push({ x: maxX, y: maxY })
    points.push({ x: minX, y: maxY })

    return points
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

  // Find nearest node
  const findNearestNode = (x: number, y: number): number | null => {
    let minDist = Infinity
    let nearestNode = null

    polygonPoints.forEach((point, index) => {
      const dist = Math.sqrt((x - point.x) ** 2 + (y - point.y) ** 2)
      if (dist < minDist && dist <= NODE_RADIUS * 2) {
        minDist = dist
        nearestNode = index
      }
    })

    return nearestNode
  }

  // Find nearest edge
  const findNearestEdge = (x: number, y: number): { index: number; t: number } | null => {
    let minDist = Infinity
    let nearestEdge = null

    for (let i = 0; i < polygonPoints.length; i++) {
      const p1 = polygonPoints[i]
      const p2 = polygonPoints[(i + 1) % polygonPoints.length]
      
      const { distance, t } = pointToLineDistance(x, y, p1.x, p1.y, p2.x, p2.y)
      
      if (distance < minDist && distance <= EDGE_DISTANCE_THRESHOLD) {
        minDist = distance
        nearestEdge = { index: i, t }
      }
    }

    return nearestEdge
  }

  // Handle canvas mouse down
  const handleMouseDown = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    // First check if clicking on a node
    const nearestNode = findNearestNode(x, y)
    if (nearestNode !== null) {
      // Handle node interaction
      if (event.shiftKey && polygonPoints.length > 3) {
        // Shift+click to delete node
        const newPoints = polygonPoints.filter((_, index) => index !== nearestNode)
        setPolygonPoints(newPoints)
        onPolygonChange(newPoints)
      } else {
        // Start dragging node
        setSelectedNode(nearestNode)
        setIsDragging(true)
      }
      return
    }

    // Check if clicking on an edge to add a new node
    const nearestEdge = findNearestEdge(x, y)
    if (nearestEdge) {
      const newPoints = [...polygonPoints]
      const p1 = newPoints[nearestEdge.index]
      const p2 = newPoints[(nearestEdge.index + 1) % newPoints.length]
      
      const newPoint: PolygonPoint = {
        x: p1.x + nearestEdge.t * (p2.x - p1.x),
        y: p1.y + nearestEdge.t * (p2.y - p1.y)
      }
      
      newPoints.splice(nearestEdge.index + 1, 0, newPoint)
      setPolygonPoints(newPoints)
      onPolygonChange(newPoints)
    }
  }

  // Handle mouse move for dragging and hover effects
  const handleMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    if (isDragging && selectedNode !== null) {
      // Update node position while dragging
      const newPoints = [...polygonPoints]
      newPoints[selectedNode] = { x, y }
      setPolygonPoints(newPoints)
      onPolygonChange(newPoints)
    } else {
      // Update hover states for visual feedback
      const nearestNode = findNearestNode(x, y)
      const nearestEdge = nearestNode === null ? findNearestEdge(x, y) : null
      
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

  // Handle mouse up
  const handleMouseUp = () => {
    setIsDragging(false)
    setSelectedNode(null)
  }

  // Draw polygon on canvas
  const drawPolygon = useCallback(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    ctx.clearRect(0, 0, width, height)

    if (polygonPoints.length < 2) return

    // Draw filled polygon background (semi-transparent)
    if (polygonPoints.length >= 3) {
      ctx.fillStyle = 'rgba(0, 255, 0, 0.2)'
      ctx.beginPath()
      ctx.moveTo(polygonPoints[0].x, polygonPoints[0].y)
      for (let i = 1; i < polygonPoints.length; i++) {
        ctx.lineTo(polygonPoints[i].x, polygonPoints[i].y)
      }
      ctx.closePath()
      ctx.fill()
    }

    // Draw edges
    polygonPoints.forEach((point, index) => {
      const nextIndex = (index + 1) % polygonPoints.length
      const nextPoint = polygonPoints[nextIndex]
      
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
    polygonPoints.forEach((point, index) => {
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
  }, [polygonPoints, selectedNode, hoveredNode, hoveredEdge, width, height])

  // Initialize polygon from mask
  useEffect(() => {
    if (maskData && polygonPoints.length === 0) {
      maskToPolygon(maskData).then(points => {
        if (Array.isArray(points)) {
          setPolygonPoints(points)
          onPolygonChange(points)
        }
      })
    }
  }, [maskData, polygonPoints.length, maskToPolygon, onPolygonChange])

  // Redraw when polygon changes
  useEffect(() => {
    drawPolygon()
  }, [drawPolygon])

  // Generate mask from polygon
  const handleGenerateMask = () => {
    const maskData = polygonToMask(polygonPoints)
    onMaskGenerated(maskData)
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Polygon Editor
      </Typography>
      
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Drag nodes • Click edges to add nodes • Shift+click nodes to delete
        </Typography>

        <ButtonGroup size="small">
          <Button onClick={handleGenerateMask} variant="contained">
            Apply Changes
          </Button>
          <Button onClick={() => setPolygonPoints([])} variant="outlined">
            Reset
          </Button>
        </ButtonGroup>
      </Box>

      <Box
        sx={{
          position: 'relative',
          width,
          height,
          border: '1px solid #ccc',
          cursor: isDragging ? 'grabbing' : 'default'
        }}
      >
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{
            display: 'block'
          }}
        />
      </Box>

    </Box>
  )
}