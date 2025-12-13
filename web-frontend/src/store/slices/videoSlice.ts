import { Video } from '@/types'
import { videoAPI } from '@/utils/api'
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'

interface VideoState {
  videos: Video[]
  currentVideo: Video | null
  currentFrame: number
  frameImageUrl: string | null
  loading: boolean
  error: string | null
}

const initialState: VideoState = {
  videos: [],
  currentVideo: null,
  currentFrame: 0,
  frameImageUrl: null,
  loading: false,
  error: null,
}

export const uploadVideo = createAsyncThunk(
  'video/uploadVideo',
  async ({ projectId, file }: { projectId: number; file: File }) => {
    const response = await videoAPI.uploadVideo(projectId, file)
    return response
  }
)

export const fetchVideos = createAsyncThunk(
  'video/fetchVideos',
  async (projectId: number) => {
    const response = await videoAPI.getVideos(projectId)
    return response
  }
)

export const fetchVideo = createAsyncThunk(
  'video/fetchVideo',
  async (videoId: number) => {
    const response = await videoAPI.getVideo(videoId)
    return response
  }
)

export const fetchFrame = createAsyncThunk(
  'video/fetchFrame',
  async ({ videoId, frameNumber }: { videoId: number; frameNumber: number }) => {
    const imageUrl = await videoAPI.getFrame(videoId, frameNumber)
    return { frameNumber, imageUrl }
  }
)

export const deleteVideo = createAsyncThunk(
  'video/deleteVideo',
  async (videoId: number) => {
    await videoAPI.deleteVideo(videoId)
    return videoId
  }
)

const videoSlice = createSlice({
  name: 'video',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    setCurrentVideo: (state, action) => {
      state.currentVideo = action.payload
    },
    setCurrentFrame: (state, action) => {
      state.currentFrame = action.payload
    },
    clearFrameImage: (state) => {
      if (state.frameImageUrl) {
        URL.revokeObjectURL(state.frameImageUrl)
        state.frameImageUrl = null
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(uploadVideo.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(uploadVideo.fulfilled, (state, action) => {
        state.loading = false
        state.videos.push(action.payload)
      })
      .addCase(uploadVideo.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to upload video'
      })
      .addCase(fetchVideos.fulfilled, (state, action) => {
        state.videos = action.payload
      })
      .addCase(fetchVideo.fulfilled, (state, action) => {
        state.currentVideo = action.payload
      })
      .addCase(fetchFrame.fulfilled, (state, action) => {
        if (state.frameImageUrl) {
          URL.revokeObjectURL(state.frameImageUrl)
        }
        state.currentFrame = action.payload.frameNumber
        state.frameImageUrl = action.payload.imageUrl
      })
      .addCase(deleteVideo.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(deleteVideo.fulfilled, (state, action) => {
        state.loading = false
        state.videos = state.videos.filter(video => video.id !== action.payload)
      })
      .addCase(deleteVideo.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to delete video'
      })
  },
})

export const { clearError, setCurrentVideo, setCurrentFrame, clearFrameImage } = videoSlice.actions
export default videoSlice.reducer
