/**
 * SAM 2 Video Annotation Controls
 *
 * This component provides the UI for SAM 2 video-based segmentation:
 * - Session initialization
 * - Object tracking
 * - Mask propagation
 * - Visual feedback for tracked objects
 */

import {
  clearSAM2Error,
  closeSAM2Session,
  initializeSAM2Session,
  propagateSAM2Masks,
  resetSAM2State,
  saveSAM2MasksToDatabase,
  startBoundaryEditing,
  stopBoundaryEditing,
  toggleRefinementMode,
  toggleSAM2Mode,
  updateSAM2Mask
} from '@/store/slices/sam2Slice'
import { AppDispatch, RootState } from '@/store/store'
import {
  CheckCircle,
  Circle,
  Edit,
  ExpandLess,
  ExpandMore,
  PlayArrow,
  Refresh,
  Save,
  Stop,
  Tune
} from '@mui/icons-material'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Switch,
  Tooltip,
  Typography,
} from '@mui/material'
import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'

interface SAM2ControlsProps {
  videoPath: string
  videoId: number
  currentFrame: number
  onObjectClick?: (objectId: number) => void
  selectedCategory: string
  sam2PolygonPoints?: Array<{ x: number; y: number }>
}

export const SAM2Controls = ({
  videoPath,
  videoId,
  currentFrame,
  onObjectClick,
  selectedCategory,
  sam2PolygonPoints = []
}: SAM2ControlsProps) => {
  const dispatch = useDispatch<AppDispatch>()
  const [expanded, setExpanded] = useState(true)

  const {
    isEnabled,
    session,
    sessionLoading,
    sessionError,
    objects,
    nextObjectId,
    currentObjectId,
    frameMasks,
    isPropagating,
    propagationProgress,
    propagationError,
    isSaving,
    saveProgress,
    saveError,
    savedToDatabase,
    isEditingBoundary,
    editingObjectId,
    editingFrameIdx,
    isRefinementMode,
  } = useSelector((state: RootState) => state.sam2)

  // Check if current frame has masks
  const currentFrameMasks = frameMasks[currentFrame] || {}
  const hasMasksOnCurrentFrame = Object.keys(currentFrameMasks).length > 0

  // Calculate total frames with masks
  const framesWithMasks = Object.keys(frameMasks).length

  const handleToggleMode = () => {
    // Close session when disabling SAM2 mode
    if (isEnabled && session) {
      dispatch(closeSAM2Session(session.session_id))
    }
    dispatch(toggleSAM2Mode())
  }

  const handleInitializeSession = async () => {
    if (!videoPath) {
      alert('No video path available')
      return
    }
    dispatch(initializeSAM2Session(videoPath))
  }

  const handleCloseSession = () => {
    if (session) {
      dispatch(closeSAM2Session(session.session_id))
    }
  }

  const handlePropagate = () => {
    if (session) {
      dispatch(propagateSAM2Masks(session.session_id))
    }
  }

  const handleClearError = () => {
    dispatch(clearSAM2Error())
  }

  const handleReset = () => {
    if (session) {
      dispatch(closeSAM2Session(session.session_id))
    }
    dispatch(resetSAM2State())
  }

  const handleSaveToDatabase = () => {
    if (!videoId) {
      alert('No video ID available')
      return
    }
    dispatch(saveSAM2MasksToDatabase({ videoId }))
  }

  const handleEditBoundary = () => {
    // Start boundary editing for the current object on the current frame
    const currentFrameMaskObjectIds = Object.keys(currentFrameMasks).map(id => parseInt(id))

    if (currentFrameMaskObjectIds.length === 0) {
      alert('No masks on current frame to edit')
      return
    }

    // Use current object if set, otherwise use the first object with a mask on this frame
    const objectToEdit = currentObjectId !== null && currentFrameMaskObjectIds.includes(currentObjectId)
      ? currentObjectId
      : currentFrameMaskObjectIds[0]

    console.log('SAM2: Starting boundary editing', { objectToEdit, frame: currentFrame })

    dispatch(startBoundaryEditing({
      objectId: objectToEdit,
      frameIdx: currentFrame
    }))
  }

  const handleDoneEditing = async () => {
    console.log('SAM2: Done editing boundary, saving edited polygon')

    // Convert polygon points to mask
    if (sam2PolygonPoints.length >= 3 && editingObjectId !== null && editingFrameIdx !== null && session) {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      if (ctx) {
        canvas.width = 640
        canvas.height = 480
        ctx.fillStyle = 'black'
        ctx.fillRect(0, 0, 640, 480)
        ctx.fillStyle = 'white'
        ctx.beginPath()
        ctx.moveTo(sam2PolygonPoints[0].x, sam2PolygonPoints[0].y)
        for (let i = 1; i < sam2PolygonPoints.length; i++) {
          ctx.lineTo(sam2PolygonPoints[i].x, sam2PolygonPoints[i].y)
        }
        ctx.closePath()
        ctx.fill()

        const maskData = canvas.toDataURL().split(',')[1]
        console.log('SAM2: Saving edited mask', { objectId: editingObjectId, frameIdx: editingFrameIdx })

        // Update the backend SAM2 session with the edited mask
        try {
          await dispatch(updateSAM2Mask({
            sessionId: session.session_id,
            frameIdx: editingFrameIdx,
            objectId: editingObjectId,
            mask: maskData
          })).unwrap()
          console.log('SAM2: Backend updated with edited mask - will be used for propagation!')
        } catch (error) {
          console.error('SAM2: Failed to update backend with edited mask:', error)
          alert(`Failed to update mask: ${error}`)
          return
        }
      }
    }

    // Exit editing mode
    dispatch(stopBoundaryEditing())
  }

  const handleToggleRefinement = () => {
    dispatch(toggleRefinementMode())
  }

  // Helper to format color for display
  const rgbToHex = (color: number[]) => {
    return `#${color.map(c => c.toString(16).padStart(2, '0')).join('')}`
  }

  return (
    <Paper
      elevation={2}
      sx={{
        p: 2,
        mb: 2,
        border: isEnabled ? '2px solid #2196f3' : '1px solid #e0e0e0',
        backgroundColor: isEnabled ? 'rgba(33, 150, 243, 0.04)' : 'inherit',
      }}
    >
      {/* Header with toggle */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="subtitle1" fontWeight="bold">
            SAM 2 Video Mode
          </Typography>
          <Chip
            label={isEnabled ? 'ON' : 'OFF'}
            size="small"
            color={isEnabled ? 'primary' : 'default'}
          />
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Switch
            checked={isEnabled}
            onChange={handleToggleMode}
            color="primary"
          />
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={expanded && isEnabled}>
        <Divider sx={{ my: 1 }} />

        {/* Error display */}
        {(sessionError || propagationError) && (
          <Alert
            severity="error"
            onClose={handleClearError}
            sx={{ mb: 2 }}
          >
            {sessionError || propagationError}
          </Alert>
        )}

        {/* Session controls */}
        {!session ? (
          <Box sx={{ textAlign: 'center', py: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Initialize a SAM 2 session to start video annotation.
              Click once to track objects across all frames.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              startIcon={sessionLoading ? <CircularProgress size={16} color="inherit" /> : <PlayArrow />}
              onClick={handleInitializeSession}
              disabled={sessionLoading || !videoPath}
            >
              {sessionLoading ? 'Initializing...' : 'Initialize Session'}
            </Button>
          </Box>
        ) : (
          <>
            {/* Session info */}
            <Box sx={{ mb: 2, p: 1, backgroundColor: 'rgba(0,0,0,0.02)', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircle color="success" fontSize="small" />
                  <Typography variant="body2">
                    Session Active
                  </Typography>
                </Box>
                <IconButton size="small" color="error" onClick={handleCloseSession}>
                  <Stop />
                </IconButton>
              </Box>
              <Typography variant="caption" color="text.secondary">
                {session.total_frames} frames @ {session.fps.toFixed(1)} fps •
                {session.frame_width}x{session.frame_height}
              </Typography>
            </Box>

            {/* Instructions */}
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Click on the canvas</strong> to add an object.
                Use <strong>left-click</strong> for positive points (include),
                <strong>right-click</strong> for negative (exclude).
              </Typography>
            </Alert>

            {/* Tracked objects list */}
            {objects.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Tracked Objects ({objects.length})
                </Typography>
                <List dense sx={{ py: 0 }}>
                  {objects.map((obj) => (
                    <ListItem
                      key={obj.object_id}
                      sx={{
                        py: 0.5,
                        px: 1,
                        borderRadius: 1,
                        backgroundColor: currentObjectId === obj.object_id ? 'rgba(33, 150, 243, 0.1)' : 'inherit',
                        cursor: 'pointer',
                        '&:hover': {
                          backgroundColor: 'rgba(0,0,0,0.04)',
                        },
                      }}
                      onClick={() => onObjectClick?.(obj.object_id)}
                    >
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        <Circle sx={{ color: rgbToHex(obj.color), fontSize: 16 }} />
                      </ListItemIcon>
                      <ListItemText
                        primary={obj.name || `Object ${obj.object_id}`}
                        secondary={`${obj.category || 'No category'} • ${obj.frames_with_masks} frames`}
                        primaryTypographyProps={{ variant: 'body2' }}
                        secondaryTypographyProps={{ variant: 'caption' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}

            {/* Propagation controls */}
            <Divider sx={{ my: 2 }} />

            {/* Edit Boundary / Done Editing buttons - shown when there's a mask on current frame */}
            {hasMasksOnCurrentFrame && (
              <Box sx={{ mb: 2 }}>
                {!isEditingBoundary ? (
                  <>
                    <Alert severity="info" sx={{ mb: 1 }}>
                      <Typography variant="body2">
                        You can refine the mask boundary before propagating. Click below to edit the polygon.
                      </Typography>
                    </Alert>
                    <Button
                      variant="outlined"
                      color="primary"
                      startIcon={<Edit />}
                      onClick={handleEditBoundary}
                      disabled={isPropagating || isSaving}
                      fullWidth
                    >
                      Edit Boundary (Polygon)
                    </Button>
                  </>
                ) : (
                  <>
                    <Alert severity="success" sx={{ mb: 1 }}>
                      <Typography variant="body2">
                        <strong>Editing Mode:</strong> Drag nodes to adjust the boundary. Click "Done Editing" to save changes.
                      </Typography>
                    </Alert>
                    <Button
                      variant="contained"
                      color="success"
                      startIcon={<CheckCircle />}
                      onClick={handleDoneEditing}
                      disabled={isPropagating || isSaving}
                      fullWidth
                    >
                      Done Editing
                    </Button>
                  </>
                )}
              </Box>
            )}

            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
              <Button
                variant="contained"
                color="secondary"
                startIcon={isPropagating ? <CircularProgress size={16} color="inherit" /> : <Refresh />}
                onClick={handlePropagate}
                disabled={isPropagating || isSaving || objects.length === 0}
              >
                {isPropagating ? 'Propagating...' : 'Propagate to All Frames'}
              </Button>

              {/* Refinement Mode toggle - shown after propagation */}
              {framesWithMasks > 1 && (
                <Tooltip title="Enable refinement mode to click on any frame to correct drifted masks">
                  <Button
                    variant={isRefinementMode ? "contained" : "outlined"}
                    color="info"
                    startIcon={<Tune />}
                    onClick={handleToggleRefinement}
                    disabled={isPropagating || isSaving}
                  >
                    {isRefinementMode ? 'Refinement Mode ON' : 'Refinement Mode'}
                  </Button>
                </Tooltip>
              )}

              <Tooltip title="Save all propagated masks to database for export">
                <Button
                  variant="contained"
                  color="success"
                  startIcon={isSaving ? <CircularProgress size={16} color="inherit" /> : <Save />}
                  onClick={handleSaveToDatabase}
                  disabled={isSaving || isPropagating || framesWithMasks === 0}
                >
                  {isSaving ? 'Saving...' : 'Save All to Database'}
                </Button>
              </Tooltip>

              <Tooltip title="Close current session">
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  startIcon={<Stop />}
                  onClick={handleCloseSession}
                  disabled={isPropagating || isSaving}
                >
                  Close Session
                </Button>
              </Tooltip>
            </Box>

            {/* Propagation progress */}
            {isPropagating && (
              <Box sx={{ mt: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption">Propagating masks...</Typography>
                  <Typography variant="caption">{propagationProgress.toFixed(0)}%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={propagationProgress} />
              </Box>
            )}

            {/* Save progress */}
            {isSaving && (
              <Box sx={{ mt: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption">Saving to database...</Typography>
                  <Typography variant="caption">{saveProgress.toFixed(0)}%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={saveProgress} color="success" />
              </Box>
            )}

            {/* Save error */}
            {saveError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {saveError}
              </Alert>
            )}

            {/* Status summary */}
            {framesWithMasks > 0 && !isPropagating && !isSaving && (
              <Box sx={{ mt: 2, p: 1, backgroundColor: savedToDatabase ? 'rgba(76, 175, 80, 0.15)' : 'rgba(76, 175, 80, 0.1)', borderRadius: 1 }}>
                <Typography variant="body2" color="success.main">
                  ✓ Masks available for {framesWithMasks} / {session.total_frames} frames
                  {savedToDatabase && ' (Saved to database)'}
                </Typography>
                {!savedToDatabase && (
                  <Typography variant="caption" color="text.secondary">
                    Click "Save All to Database" to enable export
                  </Typography>
                )}
              </Box>
            )}
          </>
        )}
      </Collapse>

      {/* Collapsed state summary */}
      {!expanded && isEnabled && session && (
        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
          <Chip label={`${objects.length} objects`} size="small" />
          <Chip label={`${framesWithMasks} frames with masks`} size="small" />
        </Box>
      )}
    </Paper>
  )
}

export default SAM2Controls
