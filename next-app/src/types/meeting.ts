export interface User {
  user_id: number
  user_name: string
  email: string
}

export interface Meeting {
  meeting_id: number
  user_id: number
  client_contact_name: string
  client_company_name: string
  meeting_datetime: string
  duration_seconds: number
  status: string
  transcript_text: string | null
  file_name: string
  file_size: number
  error_message: string | null
}

export interface MeetingSearchParams {
  userId?: string
  fromDate?: string
  toDate?: string
}

// APIのレスポンスは配列を直接返すため、この型は不要になりました
// export interface MeetingSearchResponse {
//   meetings: Meeting[]
//   users: User[]
// } 