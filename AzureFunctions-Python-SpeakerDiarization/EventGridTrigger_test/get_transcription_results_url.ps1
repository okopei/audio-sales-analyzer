param(
    [Parameter(Mandatory=$true)]
    [string]$TranscriptionId,
    
    [Parameter(Mandatory=$true)]
    [string]$SpeechKey,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "japaneast"
)

# Speech Service APIのエンドポイント
$endpoint = "https://$Region.stt.speech.microsoft.com/speechtotext/v3.0/transcriptions/$TranscriptionId/files"

# ヘッダーを設定
$headers = @{
    "Ocp-Apim-Subscription-Key" = $SpeechKey
    "Content-Type" = "application/json"
}

try {
    Write-Host "🔍 文字起こし結果のURLを取得中..."
    Write-Host "📝 Transcription ID: $TranscriptionId"
    Write-Host "🌐 エンドポイント: $endpoint"
    
    $response = Invoke-WebRequest -Uri $endpoint -Method Get -Headers $headers
    
    # レスポンスをJSONとして解析
    $result = $response.Content | ConvertFrom-Json
    
    # channel_0のURLを探す
    $channel0Url = ($result.values | Where-Object { $_.name -eq "channel_0" }).contentUrl
    
    if ($channel0Url) {
        Write-Host "✅ 文字起こし結果のURLを取得しました！"
        Write-Host "🔗 URL: $channel0Url"
        return $channel0Url
    }
    else {
        Write-Host "⚠️ channel_0のURLが見つかりませんでした"
        Write-Host "📄 利用可能なファイル一覧:"
        $result.values | ForEach-Object {
            Write-Host "  - $($_.name): $($_.contentUrl)"
        }
        exit 1
    }
}
catch {
    Write-Host "❌ エラーが発生しました:"
    Write-Host $_.Exception.Message
    exit 1
} 