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
    
    const accountName = process.env.AZURE_STORAGE_ACCOUNT_NAME || 'audiosalesanalyzeraudio'
    const containerName = process.env.AZURE_STORAGE_CONTAINER_NAME || 'moc-audio'
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
    console.log("🟡[AZURE] SASトークン取得リクエスト送信: fileName=", fileName)
    let sasResponse;
    try {
      sasResponse = await fetch('/api/azure/get-sas-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache'
        },
        body: JSON.stringify({ fileName })
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
    const { sasUrl } = sasData
    
    if (!sasUrl) {
      console.error('SASトークンがレスポンスに含まれていません:', sasData)
      throw new Error('SASトークンがレスポンスに含まれていません')
    }
    
    // Blobサービスのエンドポイント
    const blobServiceEndpoint = `https://${accountName}.blob.core.windows.net`
    
    // Blobのアップロード先URL
    const blobUrl = sasUrl
    console.log('アップロード先URL (トークン部分なし):', blobUrl.split('?')[0])
    
    // CORS問題を回避するため、サーバーサイドでアップロードを行う
    console.log('サーバーサイドアップロード開始')
    const formData = new FormData()
    formData.append('file', file)
    formData.append('fileName', blobName)
    formData.append('sasToken', sasUrl.split('?')[1] || '')
    
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
    const accountName = process.env.AZURE_STORAGE_ACCOUNT_NAME
    const containerName = process.env.AZURE_STORAGE_CONTAINER_NAME || 'moc-audio'
    
    // SASトークンを取得するAPIエンドポイント
    const sasResponse = await fetch('/api/azure/get-sas-token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ fileName: blobName })
    })
    
    if (!sasResponse.ok) {
      throw new Error('SASトークンの取得に失敗しました')
    }
    
    const { sasUrl } = await sasResponse.json()
    
    // ダウンロード用のURL
    return sasUrl
  } catch (error) {
    console.error('ダウンロードURLの取得エラー:', error)
    throw error
  }
} 