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
  points?: Array<{ x: number, y: number, is_positive: boolean }>
  boxes?: Array<{ x1: number, y1: number, x2: number, y2: number }>
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

// ============================================================
// SAM 2 Video Annotation Types
// ============================================================

export interface SAM2Session {
  session_id: string
  video_path: string
  total_frames: number
  frame_width: number
  frame_height: number
  fps: number
}

export interface SAM2TrackedObject {
  object_id: number
  name: string
  category: string
  color: [number, number, number]
  frames_with_masks: number
}

export interface SAM2SessionStatus {
  session_id: string
  video_path: string
  total_frames: number
  objects: SAM2TrackedObject[]
  created_at: number
  last_accessed: number
  idle_time: number
}

export interface SAM2AddObjectRequest {
  session_id: string
  frame_idx: number
  object_id: number
  points: [number, number][]
  labels: number[]
  name?: string
  category?: string
}

export interface SAM2AddObjectResponse {
  object_id: number
  name: string
  category: string
  color: number[]
  frame_idx: number
  mask: string  // Base64 encoded PNG
}

export interface SAM2PropagateRequest {
  session_id: string
  start_frame?: number
  end_frame?: number
  direction?: 'forward' | 'backward' | 'both'
}

export interface SAM2FrameMask {
  frame_idx: number
  masks: Record<number, string>  // object_id -> base64 mask
}

export interface SAM2PropagateResponse {
  session_id: string
  total_frames: number
  total_objects: number
}

export interface SAM2RefineRequest {
  session_id: string
  frame_idx: number
  object_id: number
  points: [number, number][]
  labels: number[]
}

export interface SAM2RefineResponse {
  object_id: number
  frame_idx: number
  mask: string
}

export interface SAM2UpdateMaskRequest {
  session_id: string
  frame_idx: number
  object_id: number
  mask: string  // base64 encoded PNG
}

export interface SAM2UpdateMaskResponse {
  object_id: number
  frame_idx: number
  mask: string
}
