param(
    [Parameter(Mandatory=$true)]
    [string]$FileName,
    
    [Parameter(Mandatory=$false)]
    [string]$Port = "7072",
    
    [Parameter(Mandatory=$false)]
    [string]$FunctionName = "TriggerTranscriptionJob"
)

# 現在のタイムスタンプを取得
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"

# EventGridイベントデータを構築
$eventData = @{
    id = (New-Guid).ToString()
    subject = "/blobServices/default/containers/audiofiles/blobs/$FileName"
    eventType = "Microsoft.Storage.BlobCreated"
    eventTime = $timestamp
    dataVersion = "1.0"
    data = @{
        api = "PutBlob"
        clientRequestId = (New-Guid).ToString()
        requestId = (New-Guid).ToString()
        eTag = "0x8Dxxxxxxxxxxxx"
        contentType = "audio/webm"
        contentLength = 1234567
        blobType = "BlockBlob"
        url = "https://storageaccount.blob.core.windows.net/audiofiles/$FileName"
        sequencer = "000000000000000000000000000000000000000000000000"
        storageDiagnostics = @{
            batchId = (New-Guid).ToString()
        }
    }
}

$events = @($eventData)

# EventGridイベントのペイロードを構築
$payload = @{
    id = (New-Guid).ToString()
    topic = "/subscriptions/{subscription-id}/resourceGroups/Storage/providers/Microsoft.Storage/storageAccounts/my-storage-account"
    subject = "/blobServices/default/containers/audiofiles/blobs/$FileName"
    eventType = "Microsoft.Storage.BlobCreated"
    eventTime = $timestamp
    dataVersion = "1.0"
    metadataVersion = "1"
    data = $eventData
}

# ヘッダーを設定
$headers = @{
    "Content-Type" = "application/json"
    "aeg-event-type" = "Notification"
}

# ローカルのAzure FunctionsエンドポイントにPOST
$url = "http://localhost:$Port/api/$FunctionName"

try {
    Write-Host "🚀 EventGridイベントを送信中..."
    Write-Host "📝 ファイル名: $FileName"
    Write-Host "🌐 エンドポイント: $url"
    
    $response = Invoke-WebRequest -Uri $url -Method Post -Headers $headers -Body ($payload | ConvertTo-Json -Depth 10)
    
    Write-Host "✅ イベント送信成功！"
    Write-Host "📊 ステータスコード: $($response.StatusCode)"
    Write-Host "📄 レスポンス: $($response.Content)"
}
catch {
    Write-Host "❌ エラーが発生しました:"
    Write-Host $_.Exception.Message
    exit 1
} 