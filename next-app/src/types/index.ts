export interface ConversationSegment {
  segment_id: string
  user_id: string
  speaker_id: string
  meeting_id: string
  content: string
  file_name: string
  file_path: string
  file_size: number
  start_time: number
  end_time: number
  duration_seconds: number
  status: string
  inserted_datetime: string
  updated_datetime: string
  speaker_name?: string
  speaker_role?: string
  comments?: Comment[]
} 