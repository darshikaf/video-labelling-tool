import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { Project } from '@/types'
import { projectAPI } from '@/utils/api'

interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  loading: boolean
  error: string | null
}

const initialState: ProjectState = {
  projects: [],
  currentProject: null,
  loading: false,
  error: null,
}

export const fetchProjects = createAsyncThunk(
  'project/fetchProjects',
  async () => {
    const response = await projectAPI.getProjects()
    return response
  }
)

export const createProject = createAsyncThunk(
  'project/createProject',
  async ({ name, description }: { name: string; description?: string }) => {
    const response = await projectAPI.createProject(name, description)
    return response
  }
)

export const fetchProject = createAsyncThunk(
  'project/fetchProject',
  async (id: number) => {
    const response = await projectAPI.getProject(id)
    return response
  }
)

const projectSlice = createSlice({
  name: 'project',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    setCurrentProject: (state, action) => {
      state.currentProject = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchProjects.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.loading = false
        state.projects = action.payload
      })
      .addCase(fetchProjects.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch projects'
      })
      .addCase(createProject.fulfilled, (state, action) => {
        state.projects.push(action.payload)
      })
      .addCase(fetchProject.fulfilled, (state, action) => {
        state.currentProject = action.payload
      })
  },
})

export const { clearError, setCurrentProject } = projectSlice.actions
export default projectSlice.reducer