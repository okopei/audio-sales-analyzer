import { type NextRequest } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { segmentId: string } }
) {
  try {
    // TODO: 認証チェックを実装
    const baseUrl = process.env.NEXT_PUBLIC_BLOB_STORAGE_URL
    const sasToken = process.env.AZURE_STORAGE_SAS_TOKEN
    
    // TODO: segmentIdを使用して実際のファイルパスを取得する処理を実装
    const url = `${baseUrl}/audio/${params.segmentId}?${sasToken}`
    
    return Response.json({ url })
  } catch (error) {
    return Response.json(
      { error: 'URL生成に失敗しました' },
      { status: 500 }
    )
  }
} 