import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const formData = await request.formData()
    const audioFile = formData.get('audio') as Blob
    
    const uploadData = new FormData()
    uploadData.append('audio', audioFile)

    // localhost を使用
    const response = await fetch('http://127.0.0.1:8000/transcribe', {
      method: 'POST',
      body: uploadData,
    })

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error:', error)
    return NextResponse.json(
      { error: 'Failed to process audio' },
      { status: 500 }
    )
  }
} 