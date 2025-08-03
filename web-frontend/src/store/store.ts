import { configureStore } from '@reduxjs/toolkit'
import authReducer from './slices/authSlice'
import projectReducer from './slices/projectSlice'
import videoReducer from './slices/videoSlice'
import annotationReducer from './slices/annotationSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    project: projectReducer,
    video: videoReducer,
    annotation: annotationReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch