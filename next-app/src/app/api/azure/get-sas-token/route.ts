import { NextRequest, NextResponse } from 'next/server'
import { BlobServiceClient, StorageSharedKeyCredential, generateBlobSASQueryParameters, BlobSASPermissions } from '@azure/storage-blob'

/**
 * Azure Blob StorageのSASトークンを生成するAPIエンドポイント
 */
export async function GET(request: NextRequest) {
  try {
    console.log('SASトークン生成開始 (GET)')
    
    // クエリパラメータからファイル名を取得
    const { searchParams } = new URL(request.url)
    const fileName = searchParams.get('fileName')
    
    if (!fileName) {
      console.error('ファイル名が指定されていません')
      return NextResponse.json(
        { error: 'ファイル名が指定されていません' },
        { status: 400 }
      )
    }
    
    console.log('ファイル名:', fileName)
    
    const accountName = process.env.AZURE_STORAGE_ACCOUNT_NAME
    const accountKey = process.env.AZURE_STORAGE_ACCOUNT_KEY
    const containerName = process.env.AZURE_STORAGE_CONTAINER_NAME || 'moc-audio'
    
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
    
    // SASトークンを生成（特定のファイル用）
    const sasToken = generateBlobSASQueryParameters(
      {
        containerName,
        blobName: fileName,
        permissions: sasPermissions,
        expiresOn: expiryTime,
      },
      sharedKeyCredential
    ).toString()
    
    // 完全なSAS URLを構築
    const sasUrl = `https://${accountName}.blob.core.windows.net/${containerName}/${fileName}?${sasToken}`
    
    console.log('SAS URL生成成功:', {
      fileName,
      sasUrl: sasUrl.split('?')[0] // セキュリティのためSASトークン部分は省略
    })
    
    return NextResponse.json(
      { sasUrl },
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

/**
 * POSTメソッドでのSASトークン生成
 */
export async function POST(request: NextRequest) {
  try {
    console.log('SASトークン生成開始 (POST)')
    
    // リクエストボディからファイル名を取得
    const body = await request.json()
    const fileName = body.fileName
    
    if (!fileName) {
      console.error('ファイル名が指定されていません')
      return NextResponse.json(
        { error: 'ファイル名が指定されていません' },
        { status: 400 }
      )
    }
    
    console.log('ファイル名:', fileName)
    
    const accountName = process.env.AZURE_STORAGE_ACCOUNT_NAME
    const accountKey = process.env.AZURE_STORAGE_ACCOUNT_KEY
    const containerName = process.env.AZURE_STORAGE_CONTAINER_NAME || 'moc-audio'
    
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
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
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
    
    // SASトークンを生成（特定のファイル用）
    const sasToken = generateBlobSASQueryParameters(
      {
        containerName,
        blobName: fileName,
        permissions: sasPermissions,
        expiresOn: expiryTime,
      },
      sharedKeyCredential
    ).toString()
    
    // 完全なSAS URLを構築
    const sasUrl = `https://${accountName}.blob.core.windows.net/${containerName}/${fileName}?${sasToken}`
    
    console.log('SAS URL生成成功:', {
      fileName,
      sasUrl: sasUrl.split('?')[0] // セキュリティのためSASトークン部分は省略
    })
    
    return NextResponse.json(
      { sasUrl },
      { 
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
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
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
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
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    }
  )
} 