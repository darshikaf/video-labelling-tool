import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { Annotation, PolygonPoint, SAMPredictionRequest } from '@/types'
import { annotationAPI, samAPI } from '@/utils/api'

interface AnnotationState {
  annotations: Annotation[]
  currentMask: string | null
  selectedPoints: Array<{x: number, y: number, is_positive: boolean}>
  selectedBoxes: Array<{x1: number, y1: number, x2: number, y2: number}>
  polygonPoints: PolygonPoint[]
  editingMode: 'default' | 'polygon'
  promptType: 'point' | 'box'
  awaitingDecision: boolean
  loading: boolean
  error: string | null
}

const initialState: AnnotationState = {
  annotations: [],
  currentMask: null,
  selectedPoints: [],
  selectedBoxes: [],
  polygonPoints: [],
  editingMode: 'default',
  promptType: 'point',
  awaitingDecision: false,
  loading: false,
  error: null,
}

export const fetchAnnotations = createAsyncThunk(
  'annotation/fetchAnnotations',
  async (frameId: number) => {
    const response = await annotationAPI.getAnnotations(frameId)
    return response
  }
)

export const createAnnotation = createAsyncThunk(
  'annotation/createAnnotation',
  async (params: {
    frameId: number
    categoryId: number
    maskData: string
    samPoints?: string
    samBoxes?: string
  }) => {
    const response = await annotationAPI.createAnnotation(
      params.frameId,
      params.categoryId,
      params.maskData,
      params.samPoints,
      params.samBoxes
    )
    return response
  }
)

export const runSAMPrediction = createAsyncThunk(
  'annotation/runSAMPrediction',
  async (request: SAMPredictionRequest) => {
    console.log('DEBUG: runSAMPrediction thunk called with:', {
      image_data_length: request.image_data?.length,
      prompt_type: request.prompt_type,
      points: request.points,
      boxes: request.boxes
    })
    const response = await samAPI.predict(request)
    console.log('DEBUG: runSAMPrediction thunk response:', {
      mask_length: response.mask?.length,
      confidence: response.confidence
    })
    return response
  }
)

const annotationSlice = createSlice({
  name: 'annotation',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    setCurrentMask: (state, action) => {
      state.currentMask = action.payload
    },
    addPoint: (state, action) => {
      state.selectedPoints.push(action.payload)
    },
    clearPoints: (state) => {
      state.selectedPoints = []
    },
    addBox: (state, action) => {
      state.selectedBoxes.push(action.payload)
    },
    clearBoxes: (state) => {
      state.selectedBoxes = []
    },
    setPolygonPoints: (state, action) => {
      state.polygonPoints = action.payload
    },
    addPolygonPoint: (state, action) => {
      state.polygonPoints.push(action.payload)
    },
    updatePolygonPoint: (state, action) => {
      const { index, point } = action.payload
      if (index >= 0 && index < state.polygonPoints.length) {
        state.polygonPoints[index] = point
      }
    },
    removePolygonPoint: (state, action) => {
      const index = action.payload
      if (index >= 0 && index < state.polygonPoints.length && state.polygonPoints.length > 3) {
        state.polygonPoints.splice(index, 1)
      }
    },
    setEditingMode: (state, action) => {
      state.editingMode = action.payload
    },
    setPromptType: (state, action) => {
      state.promptType = action.payload
    },
    setAwaitingDecision: (state, action) => {
      state.awaitingDecision = action.payload
    },
    resetAnnotationState: (state) => {
      state.currentMask = null
      state.selectedPoints = []
      state.selectedBoxes = []
      state.polygonPoints = []
      state.editingMode = 'default'
      state.awaitingDecision = false
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAnnotations.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchAnnotations.fulfilled, (state, action) => {
        state.loading = false
        state.annotations = action.payload
      })
      .addCase(fetchAnnotations.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch annotations'
      })
      .addCase(createAnnotation.fulfilled, (state, action) => {
        state.annotations.push(action.payload)
        state.currentMask = null
        state.selectedPoints = []
        state.selectedBoxes = []
        state.awaitingDecision = false
      })
      .addCase(runSAMPrediction.pending, (state) => {
        console.log('DEBUG: Redux - SAM prediction pending')
        state.loading = true
        state.error = null
      })
      .addCase(runSAMPrediction.fulfilled, (state, action) => {
        console.log('DEBUG: Redux - SAM prediction fulfilled with:', {
          mask_length: action.payload.mask?.length,
          confidence: action.payload.confidence
        })
        state.loading = false
        state.currentMask = action.payload.mask
        state.awaitingDecision = true
        console.log('DEBUG: Redux - currentMask set to:', state.currentMask?.substring(0, 50))
      })
      .addCase(runSAMPrediction.rejected, (state, action) => {
        console.log('DEBUG: Redux - SAM prediction rejected:', action.error.message)
        state.loading = false
        state.error = action.error.message || 'SAM prediction failed'
      })
  },
})

export const {
  clearError,
  setCurrentMask,
  addPoint,
  clearPoints,
  addBox,
  clearBoxes,
  setPolygonPoints,
  addPolygonPoint,
  updatePolygonPoint,
  removePolygonPoint,
  setEditingMode,
  setPromptType,
  setAwaitingDecision,
  resetAnnotationState,
} = annotationSlice.actions

export default annotationSlice.reducer