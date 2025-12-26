import { configureStore } from '@reduxjs/toolkit'
import annotationReducer from './slices/annotationSlice'
import authReducer from './slices/authSlice'
import projectReducer from './slices/projectSlice'
import sam2Reducer from './slices/sam2Slice'
import videoReducer from './slices/videoSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    project: projectReducer,
    video: videoReducer,
    annotation: annotationReducer,
    sam2: sam2Reducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
