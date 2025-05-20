export interface CommentReader {
  reader_id: number
  read_datetime: string
}

export interface Comment {
  comment_id: number
  segment_id: number
  meeting_id: number
  user_id: number
  user_name: string
  content: string
  inserted_datetime: string
  updated_datetime: string
  readers: CommentReader[] // 既読ユーザー情報の配列
} 