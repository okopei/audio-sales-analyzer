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
    let formData;
    try {
      formData = await request.formData()
    } catch (formError) {
      console.error('Form-dataの解析に失敗しました:', formError)
      return NextResponse.json(
        { error: `Form-dataの解析に失敗しました: ${formError instanceof Error ? formError.message : String(formError)}` },
        { status: 400 }
      )
    }
    
    const file = formData.get('file') as File
    const fileName = formData.get('fileName') as string
    const sasToken = formData.get('sasToken') as string
    
    if (!file || !fileName || !sasToken) {
      console.error('必要なパラメータが不足しています', { 
        hasFile: !!file, 
        hasFileName: !!fileName, 
        hasSasToken: !!sasToken,
        fileSize: file ? file.size : 0,
        fileType: file ? file.type : 'なし' 
      })
      return NextResponse.json(
        { error: '必要なパラメータが不足しています' },
        { status: 400 }
      )
    }
    
    console.log('アップロード情報:', { 
      fileName, 
      fileSize: file.size, 
      fileType: file.type,
      sasTokenLength: sasToken.length
    })
    
    // ファイルをバッファに変換
    let buffer;
    try {
      buffer = await file.arrayBuffer()
      console.log('ファイルをバッファに変換しました:', { bufferSize: buffer.byteLength })
    } catch (bufferError) {
      console.error('ファイルのバッファ変換に失敗しました:', bufferError)
      return NextResponse.json(
        { error: `ファイルのバッファ変換に失敗しました: ${bufferError instanceof Error ? bufferError.message : String(bufferError)}` },
        { status: 500 }
      )
    }
    
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
    
    // BlobServiceClientの作成
    let blobServiceClient;
    try {
      blobServiceClient = BlobServiceClient.fromConnectionString(connectionString)
    } catch (clientError) {
      console.error('BlobServiceClientの作成に失敗しました:', clientError)
      return NextResponse.json(
        { error: `BlobServiceClientの作成に失敗しました: ${clientError instanceof Error ? clientError.message : String(clientError)}` },
        { status: 500 }
      )
    }
    
    const containerClient = blobServiceClient.getContainerClient(containerName)
    const blockBlobClient = containerClient.getBlockBlobClient(fileName)
    
    console.log('Blobアップロード開始:', {
      containerName,
      blobName: fileName,
      fileSize: buffer.byteLength,
      url: blockBlobClient.url.split('?')[0] // SASトークンなしのURL
    })
    
    // ファイルをアップロード
    let uploadResponse;
    try {
      uploadResponse = await blockBlobClient.uploadData(Buffer.from(buffer), {
        blobHTTPHeaders: {
          blobContentType: file.type
        }
      })
      console.log('Blobアップロード完了:', {
        requestId: uploadResponse.requestId,
        etag: uploadResponse.etag,
        date: uploadResponse.date?.toISOString()
      })
    } catch (uploadError) {
      console.error('Blobアップロードに失敗しました:', uploadError)
      return NextResponse.json(
        { error: `Blobアップロードに失敗しました: ${uploadError instanceof Error ? uploadError.message : String(uploadError)}` },
        { status: 500 }
      )
    }
    
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