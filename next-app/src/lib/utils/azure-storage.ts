/**
 * Azure Blob Storageを操作するためのユーティリティ関数
 */

/**
 * Azure Blob Storageにファイルをアップロードする
 * @param file アップロードするファイル
 * @param fileName ファイル名（省略時はファイルの名前を使用）
 * @returns アップロードされたBlobのURL
 */
export async function uploadToAzureStorage(file: File, fileName?: string): Promise<string> {
  try {
    console.log('アップロード開始:', fileName || file.name, `(${file.size} bytes)`)
    
    const accountName = process.env.NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME
    const containerName = process.env.NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME || 'moc-audio'
    const blobName = fileName || file.name
    
    console.log('環境変数確認:', { 
      accountName: accountName || '未設定', 
      containerName: containerName || '未設定'
    })
    
    if (!accountName) {
      throw new Error('ストレージアカウント名が設定されていません')
    }

    // SASトークンを取得するAPIエンドポイント
    console.log('SASトークン取得開始')
    let sasResponse;
    try {
      sasResponse = await fetch('/api/azure/get-sas-token', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache'
        }
      })
    } catch (fetchError) {
      console.error('SASトークン取得時のネットワークエラー:', fetchError)
      throw new Error(`SASトークン取得時のネットワークエラー: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`)
    }
    
    if (!sasResponse.ok) {
      const errorText = await sasResponse.text()
      console.error('SASトークン取得エラー:', sasResponse.status, errorText)
      throw new Error(`SASトークンの取得に失敗しました: ${sasResponse.status} ${errorText}`)
    }
    
    let sasData;
    try {
      sasData = await sasResponse.json()
    } catch (jsonError) {
      console.error('SASトークンのJSONパースエラー:', jsonError)
      throw new Error('SASトークンの応答が正しいJSON形式ではありません')
    }

    console.log('SASトークン取得成功')
    const { sasToken } = sasData
    
    if (!sasToken) {
      console.error('SASトークンがレスポンスに含まれていません:', sasData)
      throw new Error('SASトークンがレスポンスに含まれていません')
    }
    
    // Blobサービスのエンドポイント
    const blobServiceEndpoint = `https://${accountName}.blob.core.windows.net`
    
    // Blobのアップロード先URL
    const blobUrl = `${blobServiceEndpoint}/${containerName}/${blobName}${sasToken}`
    console.log('アップロード先URL (トークン部分なし):', blobUrl.split('?')[0])
    
    // CORS問題を回避するため、サーバーサイドでアップロードを行う
    console.log('サーバーサイドアップロード開始')
    const formData = new FormData()
    formData.append('file', file)
    formData.append('fileName', blobName)
    formData.append('sasToken', sasToken)
    
    let uploadResponse;
    try {
      uploadResponse = await fetch('/api/azure/upload-blob', {
        method: 'POST',
        body: formData,
      })
    } catch (uploadFetchError) {
      console.error('サーバーサイドアップロード時のネットワークエラー:', uploadFetchError)
      throw new Error(`サーバーサイドアップロード時のネットワークエラー: ${uploadFetchError instanceof Error ? uploadFetchError.message : String(uploadFetchError)}`)
    }
    
    if (!uploadResponse.ok) {
      const errorText = await uploadResponse.text()
      console.error('サーバーサイドアップロードエラー:', uploadResponse.status, errorText)
      throw new Error(`ファイルのアップロードに失敗しました: ${uploadResponse.status} ${errorText}`)
    }
    
    const uploadResult = await uploadResponse.json()
    console.log('サーバーサイドアップロード成功:', uploadResult)
    
    // アップロードされたBlobのURL（SASトークンなし）
    return `${blobServiceEndpoint}/${containerName}/${blobName}`
  } catch (error) {
    console.error('Azure Storageへのアップロードエラー:', error)
    throw error
  }
}

/**
 * Azure Blob StorageからファイルをダウンロードするURLを取得する
 * @param blobName Blobの名前
 * @returns ダウンロード用のURL（SASトークン付き）
 */
export async function getAzureStorageDownloadUrl(blobName: string): Promise<string> {
  try {
    const accountName = process.env.NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME
    const containerName = process.env.NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME || 'moc-audio'
    
    // SASトークンを取得するAPIエンドポイント
    const sasResponse = await fetch('/api/azure/get-sas-token', {
      method: 'GET',
    })
    
    if (!sasResponse.ok) {
      throw new Error('SASトークンの取得に失敗しました')
    }
    
    const { sasToken } = await sasResponse.json()
    
    // ダウンロード用のURL
    return `https://${accountName}.blob.core.windows.net/${containerName}/${blobName}${sasToken}`
  } catch (error) {
    console.error('ダウンロードURLの取得エラー:', error)
    throw error
  }
} 