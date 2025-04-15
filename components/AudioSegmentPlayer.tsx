'use client'

import { PlayIcon, StopIcon } from '@heroicons/react/24/solid'
import { useState, useRef, useEffect } from 'react'

interface AudioSegmentPlayerProps {
  audioUrl: string
  startTime: number
  endTime: number
  segmentId: number
}

const AudioSegmentPlayer: React.FC<AudioSegmentPlayerProps> = ({ 
  audioUrl,
  startTime = 0,
  endTime = 0,
  segmentId
}) => {
  return (
    <div>
      {/* 新しい実装をここに追加 */}
    </div>
  )
}

export default AudioSegmentPlayer