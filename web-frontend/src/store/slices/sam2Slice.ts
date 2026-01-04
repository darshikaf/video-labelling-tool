import {
  SAM2AddObjectRequest,
  SAM2Session,
  SAM2TrackedObject
} from '@/types'
import { annotationAPI, sam2API } from '@/utils/api'
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

  // Save to database state
  isSaving: boolean
  saveProgress: number
  saveError: string | null
  savedToDatabase: boolean

  // Boundary editing state (for polygon editing before propagation)
  isEditingBoundary: boolean
  editingObjectId: number | null
  editingFrameIdx: number | null

  // Refinement state (for click-based corrections after propagation)
  isRefinementMode: boolean

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
  isSaving: false,
  saveProgress: 0,
  saveError: null,
  savedToDatabase: false,
  isEditingBoundary: false,
  editingObjectId: null,
  editingFrameIdx: null,
  isRefinementMode: false,
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

export const updateSAM2Mask = createAsyncThunk(
  'sam2/updateMask',
  async (request: {
    sessionId: string
    frameIdx: number
    objectId: number
    mask: string
  }, { rejectWithValue }) => {
    try {
      const response = await sam2API.updateMask({
        session_id: request.sessionId,
        frame_idx: request.frameIdx,
        object_id: request.objectId,
        mask: request.mask,
      })
      return { frameIdx: request.frameIdx, response }
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to update mask')
    }
  }
)

export const fetchFrameMasks = createAsyncThunk(
  'sam2/fetchFrameMasks',
  async (request: {
    sessionId: string
    frameIdx: number
  }, { rejectWithValue, getState }) => {
    try {
      // Check if masks are already loaded for this frame
      const state = getState() as { sam2: SAM2State }
      if (state.sam2.frameMasks[request.frameIdx]) {
        // Already loaded, return cached data
        return { frameIdx: request.frameIdx, masks: state.sam2.frameMasks[request.frameIdx] }
      }

      // Fetch from server
      const masks = await sam2API.getFrameMasks(request.sessionId, request.frameIdx)
      return { frameIdx: request.frameIdx, masks }
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch frame masks')
    }
  }
)

export const saveSAM2MasksToDatabase = createAsyncThunk(
  'sam2/saveToDatabase',
  async (
    { videoId }: { videoId: number },
    { getState, dispatch, rejectWithValue }
  ) => {
    try {
      const state = getState() as { sam2: SAM2State }
      const { frameMasks, objects } = state.sam2

      // Check if there are masks to save
      const totalFrames = Object.keys(frameMasks).length
      if (totalFrames === 0) {
        return rejectWithValue('No masks to save. Run propagation first.')
      }

      console.log(`SAM2: Saving masks for ${totalFrames} frames to database`)

      // Use the batch save API
      const result = await annotationAPI.saveSAM2Masks(
        videoId,
        frameMasks,
        objects.map(obj => ({
          object_id: obj.object_id,
          name: obj.name,
          category: obj.category,
        })),
        (saved, total) => {
          // Update progress
          const progress = Math.round((saved / total) * 100)
          dispatch(setSaveProgress(progress))
        }
      )

      return result
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to save masks to database')
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
    setSaveProgress: (state, action: PayloadAction<number>) => {
      state.saveProgress = action.payload
    },
    clearSAM2Error: (state) => {
      state.sessionError = null
      state.propagationError = null
      state.saveError = null
    },
    setFrameMask: (state, action: PayloadAction<{ frameIdx: number; objectId: number; mask: string }>) => {
      const { frameIdx, objectId, mask } = action.payload
      if (!state.frameMasks[frameIdx]) {
        state.frameMasks[frameIdx] = {}
      }
      state.frameMasks[frameIdx][objectId] = mask
    },
    // Boundary editing actions
    startBoundaryEditing: (state, action: PayloadAction<{ objectId: number; frameIdx: number }>) => {
      state.isEditingBoundary = true
      state.editingObjectId = action.payload.objectId
      state.editingFrameIdx = action.payload.frameIdx
    },
    stopBoundaryEditing: (state) => {
      state.isEditingBoundary = false
      state.editingObjectId = null
      state.editingFrameIdx = null
    },
    updateMaskAfterBoundaryEdit: (state, action: PayloadAction<{ frameIdx: number; objectId: number; mask: string }>) => {
      const { frameIdx, objectId, mask } = action.payload
      if (!state.frameMasks[frameIdx]) {
        state.frameMasks[frameIdx] = {}
      }
      state.frameMasks[frameIdx][objectId] = mask
      // Exit boundary editing mode after updating mask
      state.isEditingBoundary = false
      state.editingObjectId = null
      state.editingFrameIdx = null
    },
    // Refinement mode actions
    enableRefinementMode: (state) => {
      state.isRefinementMode = true
    },
    disableRefinementMode: (state) => {
      state.isRefinementMode = false
    },
    toggleRefinementMode: (state) => {
      state.isRefinementMode = !state.isRefinementMode
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

        // Response now only contains metadata - masks will be fetched on-demand
        const response = action.payload
        console.log('SAM2: Propagation complete:', {
          total_frames: response.total_frames,
          total_objects: response.total_objects
        })

        // Note: Object frame counts will be updated as masks are fetched on-demand
        // For now, assume all frames have masks after propagation
        for (const obj of state.objects) {
          obj.frames_with_masks = response.total_frames
        }
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

      // Update mask
      .addCase(updateSAM2Mask.fulfilled, (state, action) => {
        const { frameIdx, response } = action.payload
        if (!state.frameMasks[frameIdx]) {
          state.frameMasks[frameIdx] = {}
        }
        state.frameMasks[frameIdx][response.object_id] = response.mask
      })

      // Fetch frame masks on-demand
      .addCase(fetchFrameMasks.fulfilled, (state, action) => {
        const { frameIdx, masks } = action.payload
        state.frameMasks[frameIdx] = masks
        console.log(`SAM2: Fetched masks for frame ${frameIdx}`, masks)
      })

      // Save to database
      .addCase(saveSAM2MasksToDatabase.pending, (state) => {
        state.isSaving = true
        state.saveProgress = 0
        state.saveError = null
        state.savedToDatabase = false
      })
      .addCase(saveSAM2MasksToDatabase.fulfilled, (state, action) => {
        state.isSaving = false
        state.saveProgress = 100
        state.savedToDatabase = true
        console.log('SAM2: Saved to database:', action.payload)
      })
      .addCase(saveSAM2MasksToDatabase.rejected, (state, action) => {
        state.isSaving = false
        state.saveError = action.payload as string
        console.error('SAM2: Save to database failed:', action.payload)
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
  setSaveProgress,
  clearSAM2Error,
  setFrameMask,
  startBoundaryEditing,
  stopBoundaryEditing,
  updateMaskAfterBoundaryEdit,
  enableRefinementMode,
  disableRefinementMode,
  toggleRefinementMode,
  resetSAM2State,
} = sam2Slice.actions

export default sam2Slice.reducer
