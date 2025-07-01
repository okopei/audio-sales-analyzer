import { NextRequest } from "next/server"
import {
  BlobSASPermissions,
  StorageSharedKeyCredential,
  generateBlobSASQueryParameters,
  SASProtocol
} from "@azure/storage-blob"

const accountName = process.env.NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME!
const accountKey = process.env.AZURE_STORAGE_ACCOUNT_KEY!
const containerName = process.env.NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME || "moc-audio"

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
      permissions: BlobSASPermissions.parse("cw"),
      startsOn: new Date(),
      expiresOn: new Date(new Date().valueOf() + 10 * 60 * 1000),
      protocol: SASProtocol.Https
    }, sharedKeyCredential).toString()

    const url = `https://${accountName}.blob.core.windows.net/${containerName}/${fileName}?${sas}`

    return new Response(JSON.stringify({ url }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  } catch (err) {
    console.error("SAS URL発行エラー:", err)
    return new Response(JSON.stringify({ error: "Internal Server Error" }), { status: 500 })
  }
} 