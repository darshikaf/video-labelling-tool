import {
  SAM2AddObjectRequest,
  SAM2Session,
  SAM2TrackedObject
} from '@/types'
import { sam2API } from '@/utils/api'
import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit'

interface SAM2State {
  // Mode
  isEnabled: boolean

  // Session
  session: SAM2Session | null
  sessionLoading: boolean
  sessionError: string | null

  // Tracked objects
  objects: SAM2TrackedObject[]
  nextObjectId: number

  // Current state
  currentObjectId: number | null

  // Masks for all frames
  frameMasks: Record<number, Record<number, string>>  // frameIdx -> objectId -> mask

  // Propagation state
  isPropagating: boolean
  propagationProgress: number
  propagationError: string | null

  // UI state
  pendingClick: { x: number; y: number; isPositive: boolean } | null
}

const initialState: SAM2State = {
  isEnabled: false,
  session: null,
  sessionLoading: false,
  sessionError: null,
  objects: [],
  nextObjectId: 1,
  currentObjectId: null,
  frameMasks: {},
  isPropagating: false,
  propagationProgress: 0,
  propagationError: null,
  pendingClick: null,
}

// Async thunks

export const initializeSAM2Session = createAsyncThunk(
  'sam2/initializeSession',
  async (videoPath: string, { rejectWithValue }) => {
    try {
      const session = await sam2API.initializeSession(videoPath)
      return session
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to initialize SAM 2 session')
    }
  }
)

export const closeSAM2Session = createAsyncThunk(
  'sam2/closeSession',
  async (sessionId: string, { rejectWithValue }) => {
    try {
      await sam2API.closeSession(sessionId)
      return sessionId
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to close session')
    }
  }
)

export const addSAM2Object = createAsyncThunk(
  'sam2/addObject',
  async (request: SAM2AddObjectRequest, { rejectWithValue }) => {
    try {
      const response = await sam2API.addObject(request)
      return { request, response }
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to add object')
    }
  }
)

export const propagateSAM2Masks = createAsyncThunk(
  'sam2/propagate',
  async (sessionId: string, { rejectWithValue, dispatch }) => {
    try {
      const response = await sam2API.propagate(
        { session_id: sessionId },
        (progress) => {
          dispatch(setPropagationProgress(progress))
        }
      )
      return response
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to propagate masks')
    }
  }
)

export const refineSAM2Mask = createAsyncThunk(
  'sam2/refine',
  async (request: {
    sessionId: string
    frameIdx: number
    objectId: number
    points: [number, number][]
    labels: number[]
  }, { rejectWithValue }) => {
    try {
      const response = await sam2API.refine({
        session_id: request.sessionId,
        frame_idx: request.frameIdx,
        object_id: request.objectId,
        points: request.points,
        labels: request.labels,
      })
      return { frameIdx: request.frameIdx, response }
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to refine mask')
    }
  }
)

const sam2Slice = createSlice({
  name: 'sam2',
  initialState,
  reducers: {
    enableSAM2Mode: (state) => {
      state.isEnabled = true
    },
    disableSAM2Mode: (state) => {
      state.isEnabled = false
    },
    toggleSAM2Mode: (state) => {
      state.isEnabled = !state.isEnabled
    },
    setCurrentObjectId: (state, action: PayloadAction<number | null>) => {
      state.currentObjectId = action.payload
    },
    setPendingClick: (state, action: PayloadAction<{ x: number; y: number; isPositive: boolean } | null>) => {
      state.pendingClick = action.payload
    },
    setPropagationProgress: (state, action: PayloadAction<number>) => {
      state.propagationProgress = action.payload
    },
    clearSAM2Error: (state) => {
      state.sessionError = null
      state.propagationError = null
    },
    setFrameMask: (state, action: PayloadAction<{ frameIdx: number; objectId: number; mask: string }>) => {
      const { frameIdx, objectId, mask } = action.payload
      if (!state.frameMasks[frameIdx]) {
        state.frameMasks[frameIdx] = {}
      }
      state.frameMasks[frameIdx][objectId] = mask
    },
    resetSAM2State: () => initialState,
  },
  extraReducers: (builder) => {
    builder
      // Initialize session
      .addCase(initializeSAM2Session.pending, (state) => {
        state.sessionLoading = true
        state.sessionError = null
      })
      .addCase(initializeSAM2Session.fulfilled, (state, action) => {
        state.sessionLoading = false
        state.session = action.payload
        state.objects = []
        state.nextObjectId = 1
        state.frameMasks = {}
        console.log('SAM2: Session initialized', action.payload)
      })
      .addCase(initializeSAM2Session.rejected, (state, action) => {
        state.sessionLoading = false
        state.sessionError = action.payload as string
        console.error('SAM2: Session initialization failed', action.payload)
      })

      // Close session
      .addCase(closeSAM2Session.fulfilled, (state) => {
        state.session = null
        state.objects = []
        state.frameMasks = {}
        state.currentObjectId = null
      })

      // Add object
      .addCase(addSAM2Object.pending, (state) => {
        state.sessionLoading = true
      })
      .addCase(addSAM2Object.fulfilled, (state, action) => {
        state.sessionLoading = false
        const { request, response } = action.payload

        // Add to tracked objects
        state.objects.push({
          object_id: response.object_id,
          name: response.name,
          category: response.category,
          color: response.color as [number, number, number],
          frames_with_masks: 1,
        })

        // Store the initial mask
        if (!state.frameMasks[request.frame_idx]) {
          state.frameMasks[request.frame_idx] = {}
        }
        state.frameMasks[request.frame_idx][response.object_id] = response.mask

        // Update next object ID
        state.nextObjectId = Math.max(state.nextObjectId, response.object_id + 1)
        state.currentObjectId = response.object_id
        state.pendingClick = null

        console.log('SAM2: Object added', response)
      })
      .addCase(addSAM2Object.rejected, (state, action) => {
        state.sessionLoading = false
        state.sessionError = action.payload as string
        state.pendingClick = null
      })

      // Propagate masks
      .addCase(propagateSAM2Masks.pending, (state) => {
        state.isPropagating = true
        state.propagationProgress = 0
        state.propagationError = null
      })
      .addCase(propagateSAM2Masks.fulfilled, (state, action) => {
        state.isPropagating = false
        state.propagationProgress = 100

        // Store all propagated masks
        const response = action.payload
        for (const frameMask of response.frames) {
          if (!state.frameMasks[frameMask.frame_idx]) {
            state.frameMasks[frameMask.frame_idx] = {}
          }
          for (const [objectIdStr, mask] of Object.entries(frameMask.masks)) {
            state.frameMasks[frameMask.frame_idx][parseInt(objectIdStr)] = mask
          }
        }

        // Update object frame counts
        for (const obj of state.objects) {
          const framesWithMask = Object.keys(state.frameMasks).filter(
            frameIdx => state.frameMasks[parseInt(frameIdx)][obj.object_id]
          ).length
          obj.frames_with_masks = framesWithMask
        }

        console.log('SAM2: Propagation complete', {
          frames: response.frames.length,
          objects: state.objects.length
        })
      })
      .addCase(propagateSAM2Masks.rejected, (state, action) => {
        state.isPropagating = false
        state.propagationError = action.payload as string
      })

      // Refine mask
      .addCase(refineSAM2Mask.fulfilled, (state, action) => {
        const { frameIdx, response } = action.payload
        if (!state.frameMasks[frameIdx]) {
          state.frameMasks[frameIdx] = {}
        }
        state.frameMasks[frameIdx][response.object_id] = response.mask
      })
  },
})

export const {
  enableSAM2Mode,
  disableSAM2Mode,
  toggleSAM2Mode,
  setCurrentObjectId,
  setPendingClick,
  setPropagationProgress,
  clearSAM2Error,
  setFrameMask,
  resetSAM2State,
} = sam2Slice.actions

export default sam2Slice.reducer
