param(
    [Parameter(Mandatory=$true)]
    [string]$WebhookUrl,
    
    [Parameter(Mandatory=$true)]
    [string]$JsonPath
)

# JSONファイルの存在確認
if (-not (Test-Path $JsonPath)) {
    Write-Host "❌ JSONファイルが見つかりません: $JsonPath"
    exit 1
}

try {
    # JSONファイルを読み込む
    Write-Host "📖 JSONファイルを読み込み中: $JsonPath"
    $jsonContent = Get-Content -Path $JsonPath -Raw
    
    # ヘッダーを設定
    $headers = @{
        "Content-Type" = "application/json"
    }
    
    Write-Host "🚀 Webhookを送信中..."
    Write-Host "🌐 エンドポイント: $WebhookUrl"
    
    $response = Invoke-WebRequest -Uri $WebhookUrl -Method Post -Headers $headers -Body $jsonContent
    
    Write-Host "✅ Webhook送信成功！"
    Write-Host "📊 ステータスコード: $($response.StatusCode)"
    Write-Host "📄 レスポンス: $($response.Content)"
}
catch {
    Write-Host "❌ エラーが発生しました:"
    Write-Host $_.Exception.Message
    exit 1
} 