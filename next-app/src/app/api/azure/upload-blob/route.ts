import { NextRequest, NextResponse } from 'next/server'
import { BlobServiceClient } from '@azure/storage-blob'

/**
 * サーバーサイドでAzure Blob Storageにファイルをアップロードするエンドポイント
 * CORSの問題を回避するために使用
 */
export async function POST(request: NextRequest) {
  try {
    console.log('サーバーサイドアップロード処理開始')
    
    // multipart/form-dataを処理
    const formData = await request.formData()
    const file = formData.get('file') as File
    const fileName = formData.get('fileName') as string
    const sasToken = formData.get('sasToken') as string
    
    if (!file || !fileName || !sasToken) {
      console.error('必要なパラメータが不足しています', { hasFile: !!file, hasFileName: !!fileName, hasSasToken: !!sasToken })
      return NextResponse.json(
        { error: '必要なパラメータが不足しています' },
        { status: 400 }
      )
    }
    
    console.log('アップロード情報:', { fileName, fileSize: file.size, fileType: file.type })
    
    // ファイルをバッファに変換
    const buffer = await file.arrayBuffer()
    
    // 環境変数からストレージアカウント情報を取得
    const accountName = process.env.NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME
    const containerName = process.env.NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME || 'moc-audio'
    
    if (!accountName) {
      console.error('ストレージアカウント名が設定されていません')
      return NextResponse.json(
        { error: 'ストレージアカウント名が設定されていません' },
        { status: 500 }
      )
    }
    
    // 接続文字列を使用してBlobServiceClientを作成
    const connectionString = process.env.AZURE_STORAGE_CONNECTION_STRING
    
    if (!connectionString) {
      console.error('ストレージ接続文字列が設定されていません')
      return NextResponse.json(
        { error: 'ストレージ接続文字列が設定されていません' },
        { status: 500 }
      )
    }
    
    const blobServiceClient = BlobServiceClient.fromConnectionString(connectionString)
    const containerClient = blobServiceClient.getContainerClient(containerName)
    const blockBlobClient = containerClient.getBlockBlobClient(fileName)
    
    console.log('Blobアップロード開始')
    
    // ファイルをアップロード
    const uploadResponse = await blockBlobClient.uploadData(Buffer.from(buffer), {
      blobHTTPHeaders: {
        blobContentType: file.type
      }
    })
    
    console.log('Blobアップロード完了:', uploadResponse.requestId)
    
    return NextResponse.json({
      success: true,
      fileName,
      etag: uploadResponse.etag,
      url: `https://${accountName}.blob.core.windows.net/${containerName}/${fileName}`
    })
    
  } catch (error) {
    console.error('サーバーサイドアップロードエラー:', error)
    return NextResponse.json(
      { error: `ファイルのアップロードに失敗しました: ${error instanceof Error ? error.message : String(error)}` },
      { status: 500 }
    )
  }
} 