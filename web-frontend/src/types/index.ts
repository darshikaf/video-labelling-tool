export interface User {
  id: number
  email: string
  created_at: string
}

export interface Project {
  id: number
  name: string
  description?: string
  owner_id: number
  created_at: string
  updated_at?: string
}

export interface Video {
  id: number
  project_id: number
  filename: string
  file_path: string
  file_size: number
  duration?: number
  fps?: number
  width?: number
  height?: number
  total_frames?: number
  created_at: string
  updated_at?: string
}

export interface Frame {
  id: number
  video_id: number
  frame_number: number
  width: number
  height: number
  created_at: string
}

export interface Category {
  id: number
  project_id: number
  name: string
  color?: string
  created_at: string
}

export interface Annotation {
  id: number
  frame_id: number
  category_id: number
  sam_points?: string
  sam_boxes?: string
  confidence?: number
  is_reviewed: boolean
  created_at: string
  updated_at?: string
}

export interface SAMPredictionRequest {
  image_data: string
  prompt_type: 'point' | 'box'
  points?: Array<{x: number, y: number, is_positive: boolean}>
  boxes?: Array<{x1: number, y1: number, x2: number, y2: number}>
}

export interface SAMPredictionResponse {
  mask: string
  confidence: number
  processing_time: number
  cached: boolean
}

export interface PolygonPoint {
  x: number
  y: number
}