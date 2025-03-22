import { NextResponse } from 'next/server'
import { BlobServiceClient, StorageSharedKeyCredential, generateBlobSASQueryParameters, BlobSASPermissions } from '@azure/storage-blob'

/**
 * Azure Blob StorageのSASトークンを生成するAPIエンドポイント
 */
export async function GET() {
  try {
    console.log('SASトークン生成開始')
    
    const accountName = process.env.NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME
    const accountKey = process.env.AZURE_STORAGE_ACCOUNT_KEY
    const containerName = process.env.NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME || 'moc-audio'
    
    console.log('環境変数詳細:', { 
      accountName: accountName || '未設定', 
      containerName: containerName || '未設定',
      hasAccountKey: !!accountKey,
      containerNameDefault: 'moc-audio'
    })
    
    if (!accountName || !accountKey) {
      console.error('ストレージアカウントの設定が不足しています')
      return NextResponse.json(
        { error: 'ストレージアカウントの設定が不足しています' },
        { 
          status: 500,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
          }
        }
      )
    }
    
    // 共有キー認証情報を作成
    const sharedKeyCredential = new StorageSharedKeyCredential(accountName, accountKey)
    
    // SASトークンの有効期限（1時間）
    const expiryTime = new Date()
    expiryTime.setHours(expiryTime.getHours() + 1)
    
    // SASトークンのパーミッション
    const sasPermissions = new BlobSASPermissions()
    sasPermissions.read = true
    sasPermissions.write = true
    sasPermissions.create = true
    
    // SASトークンを生成
    const sasToken = generateBlobSASQueryParameters(
      {
        containerName,
        permissions: sasPermissions,
        expiresOn: expiryTime,
      },
      sharedKeyCredential
    ).toString()
    
    console.log('SASトークン生成成功')
    
    return NextResponse.json(
      { sasToken: `?${sasToken}` },
      { 
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type'
        }
      }
    )
  } catch (error) {
    console.error('SASトークン生成エラー:', error)
    return NextResponse.json(
      { error: `SASトークンの生成に失敗しました: ${error instanceof Error ? error.message : String(error)}` },
      { 
        status: 500,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type'
        }
      }
    )
  }
}

// OPTIONSリクエストに対応するためのハンドラ
export async function OPTIONS() {
  return NextResponse.json(
    {},
    {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    }
  )
} 