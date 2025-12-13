import { Annotation, Project, SAMPredictionRequest, SAMPredictionResponse, User, Video } from '@/types'
import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios'

// Use relative URLs so Vite proxy handles routing to the backend
// In Docker: Vite proxies /api -> http://backend:8000
// In production: nginx/reverse proxy handles this
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// SAM API also goes through the main API proxy now
const samClient = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// Add auth token to all requests (except login/register)
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Handle 401 responses (token expired or invalid)
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('token')
      // Only redirect if not already on login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Add same interceptors to samClient for consistency
samClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

export const authAPI = {
  login: async (email: string, password: string) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    const response = await apiClient.post('/auth/login', formData)
    return response.data
  },

  register: async (email: string, password: string): Promise<User> => {
    const response = await apiClient.post('/auth/register', { email, password })
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get('/auth/me')
    return response.data
  },
}

export const projectAPI = {
  getProjects: async (): Promise<Project[]> => {
    const response = await apiClient.get('/projects/')
    return response.data
  },

  createProject: async (name: string, description?: string, categories?: string[], annotation_format?: string): Promise<Project> => {
    const response = await apiClient.post('/projects/', { name, description, categories, annotation_format })
    return response.data
  },

  getProject: async (id: number): Promise<Project> => {
    const response = await apiClient.get(`/projects/${id}`)
    return response.data
  },

  getProjectCategories: async (projectId: number): Promise<Array<{ id: number, name: string, color: string }>> => {
    const response = await apiClient.get(`/projects/${projectId}/categories`)
    return response.data
  },
}

export const videoAPI = {
  uploadVideo: async (projectId: number, file: File): Promise<Video> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post(`/projects/${projectId}/videos`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  getVideos: async (projectId: number): Promise<Video[]> => {
    const response = await apiClient.get(`/projects/${projectId}/videos`)
    return response.data
  },

  getVideo: async (videoId: number): Promise<Video> => {
    const response = await apiClient.get(`/videos/${videoId}`)
    return response.data
  },

  getFrame: async (videoId: number, frameNumber: number): Promise<string> => {
    const response = await apiClient.get(`/videos/${videoId}/frames/${frameNumber}`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },

  deleteVideo: async (videoId: number): Promise<void> => {
    await apiClient.delete(`/videos/${videoId}`)
  },
}

export const annotationAPI = {
  getAnnotations: async (frameId: number): Promise<Annotation[]> => {
    const response = await apiClient.get(`/frames/${frameId}/annotations`)
    return response.data
  },

  getAnnotationsForFrame: async (videoId: number, frameNumber: number): Promise<any[]> => {
    const response = await apiClient.get(`/videos/${videoId}/frames/${frameNumber}/annotations`)
    return response.data
  },

  createAnnotation: async (videoId: number, frameNumber: number, categoryName: string, maskData: string, samPoints?: any[], samBoxes?: any[], confidence?: number): Promise<any> => {
    const response = await apiClient.post(`/videos/${videoId}/frames/${frameNumber}/annotations`, {
      category_name: categoryName,
      mask_data: maskData,
      sam_points: samPoints ? JSON.stringify(samPoints) : null,
      sam_boxes: samBoxes ? JSON.stringify(samBoxes) : null,
      confidence: confidence,
    })
    return response.data
  },

  updateAnnotation: async (annotationId: number, data: Partial<Annotation>): Promise<Annotation> => {
    const response = await apiClient.put(`/annotations/${annotationId}`, data)
    return response.data
  },

  deleteAnnotation: async (annotationId: number): Promise<void> => {
    await apiClient.delete(`/annotations/${annotationId}`)
  },

  getAnnotationMaskUrl: async (annotationId: number): Promise<{ mask_url: string }> => {
    const response = await apiClient.get(`/annotations/${annotationId}/mask-url`)
    return response.data
  },
}

export const samAPI = {
  predict: async (request: SAMPredictionRequest): Promise<SAMPredictionResponse> => {
    try {
      console.log('DEBUG: samAPI.predict called with request:', {
        image_data_length: request.image_data?.length,
        prompt_type: request.prompt_type,
        points: request.points,
        boxes: request.boxes
      })

      const response = await apiClient.post('/sam/predict', request, {
        timeout: 60000, // 60 seconds timeout for SAM predictions
        headers: {
          'Content-Type': 'application/json'
        }
      })

      console.log('DEBUG: samAPI.predict response received:', {
        status: response.status,
        mask_length: response.data?.mask?.length,
        confidence: response.data?.confidence,
        processing_time: response.data?.processing_time
      })

      if (!response.data?.mask) {
        throw new Error('No mask data received from SAM API')
      }

      return response.data
    } catch (error: any) {
      console.error('DEBUG: samAPI.predict error:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        code: error.code
      })

      if (error.code === 'ECONNABORTED') {
        throw new Error('SAM prediction timed out. Please try again.')
      } else if (error.response?.status === 422) {
        throw new Error('Invalid request data for SAM prediction')
      } else if (error.response?.status === 500) {
        throw new Error('SAM prediction failed on server')
      }

      throw error
    }
  },
}

export const maskAPI = {
  adjustMask: async (maskData: string, adjustmentType: 'expand' | 'contract' | 'smooth', amount: number) => {
    try {
      const response = await apiClient.post('/masks/adjust', {
        mask_data: maskData,
        adjustment_type: adjustmentType,
        amount: amount
      })

      return response.data.adjusted_mask
    } catch (error: any) {
      console.error('Mask adjustment failed:', error)
      throw error
    }
  },
}
