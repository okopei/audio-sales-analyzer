import { NextRequest } from "next/server"
import {
  BlobSASPermissions,
  StorageSharedKeyCredential,
  generateBlobSASQueryParameters,
  SASProtocol
} from "@azure/storage-blob"

// 動的レンダリングを強制
export const dynamic = 'force-dynamic'

const accountName = "audiosalesanalyzeraudio"
const accountKey = process.env.AZURE_STORAGE_ACCOUNT_KEY!
const containerName = "moc-audio"

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const fileName = searchParams.get("fileName")
    if (!fileName) {
      return new Response(JSON.stringify({ error: "fileName is required" }), { status: 400 })
    }

    const sharedKeyCredential = new StorageSharedKeyCredential(accountName, accountKey)

    const sas = generateBlobSASQueryParameters({
      containerName,
      blobName: fileName,
      permissions: BlobSASPermissions.parse("cw"), // create + write
      startsOn: new Date(),
      expiresOn: new Date(Date.now() + 10 * 60 * 1000), // 10分有効
      protocol: SASProtocol.Https,
    }, sharedKeyCredential).toString()

    const url = `https://${accountName}.blob.core.windows.net/${containerName}/${fileName}?${sas}`

    return new Response(JSON.stringify({ url }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  } catch (err) {
    console.error("SAS発行エラー:", err)
    return new Response(JSON.stringify({ error: "Internal Server Error" }), { status: 500 })
  }
} 