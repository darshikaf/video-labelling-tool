import React, { useState, useEffect, useRef } from 'react'
import { Box, Slider, Typography, IconButton } from '@mui/material'
import { PlayArrow, Pause, SkipPrevious, SkipNext } from '@mui/icons-material'
import { Video } from '@/types'

interface VideoPlayerProps {
  video: Video | null
  currentFrame: number
  onFrameChange: (frameNumber: number) => void
  frameImageUrl: string | null
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  video,
  currentFrame,
  onFrameChange,
  frameImageUrl
}) => {
  const [isPlaying, setIsPlaying] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const totalFrames = video?.total_frames || 0
  const fps = video?.fps || 30

  useEffect(() => {
    if (isPlaying && video) {
      intervalRef.current = setInterval(() => {
        onFrameChange((prev) => {
          const next = prev + 1
          if (next >= totalFrames) {
            setIsPlaying(false)
            return prev
          }
          return next
        })
      }, 1000 / fps)
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isPlaying, video, fps, totalFrames, onFrameChange])

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying)
  }

  const handleSliderChange = (_: Event, value: number | number[]) => {
    if (typeof value === 'number') {
      onFrameChange(value)
    }
  }

  const handlePreviousFrame = () => {
    if (currentFrame > 0) {
      onFrameChange(currentFrame - 1)
    }
  }

  const handleNextFrame = () => {
    if (currentFrame < totalFrames - 1) {
      onFrameChange(currentFrame + 1)
    }
  }

  const formatTime = (frameNumber: number) => {
    if (!video) return '00:00'
    const timeInSeconds = frameNumber / fps
    const minutes = Math.floor(timeInSeconds / 60)
    const seconds = timeInSeconds % 60
    return `${minutes.toString().padStart(2, '0')}:${seconds.toFixed(2).padStart(5, '0')}`
  }

  if (!video) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No video selected
        </Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 2 }}>
      {/* Video Frame Display */}
      <Box
        sx={{
          width: 800,
          height: 600,
          backgroundColor: '#000',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid #ccc',
          mb: 2,
        }}
      >
        {frameImageUrl ? (
          <img
            src={frameImageUrl}
            alt={`Frame ${currentFrame}`}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain'
            }}
          />
        ) : (
          <Typography color="white">Loading frame...</Typography>
        )}
      </Box>

      {/* Controls */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <IconButton onClick={handlePreviousFrame} disabled={currentFrame === 0}>
          <SkipPrevious />
        </IconButton>
        <IconButton onClick={handlePlayPause}>
          {isPlaying ? <Pause /> : <PlayArrow />}
        </IconButton>
        <IconButton onClick={handleNextFrame} disabled={currentFrame >= totalFrames - 1}>
          <SkipNext />
        </IconButton>
        
        <Typography variant="body2" sx={{ minWidth: 80 }}>
          {formatTime(currentFrame)}
        </Typography>
      </Box>

      {/* Timeline Slider */}
      <Box sx={{ px: 1 }}>
        <Slider
          value={currentFrame}
          min={0}
          max={Math.max(0, totalFrames - 1)}
          onChange={handleSliderChange}
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => `Frame ${value}`}
        />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
          <Typography variant="caption">
            Frame {currentFrame} of {totalFrames}
          </Typography>
          <Typography variant="caption">
            {video.duration ? `${video.duration.toFixed(1)}s` : 'Unknown duration'}
          </Typography>
        </Box>
      </Box>
    </Box>
  )
}