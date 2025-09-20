'use client'

import { useState, useRef, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { VideoSummary, CropRegion } from "@/lib/video-schemas"
import { updateCropRegion } from "@/lib/video-api"
import { toast } from "sonner"
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize,
  Move,
  Save,
  RotateCcw,
  Loader2,
  Video as VideoIcon,
  AlertTriangle
} from "lucide-react"
import { cn } from "@/lib/utils"

interface VideoPreviewProps {
  jobId: string
  summary: VideoSummary
  videoUrl: string
  initialCropRegion?: CropRegion
  faceDetectionConfidence?: number
  onCropChange?: (cropRegion: CropRegion) => void
  onBulletPointsChange?: (bulletPoints: VideoSummary['bullet_points']) => void
  onDurationChange?: (duration: number) => void
  className?: string
}

export function VideoPreview({
  jobId,
  summary,
  videoUrl,
  initialCropRegion = { x: 0, y: 0, width: 640, height: 480 },
  faceDetectionConfidence = 0.82,
  onCropChange,
  onBulletPointsChange,
  onDurationChange,
  className
}: VideoPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  
  const [cropRegion, setCropRegion] = useState<CropRegion>(initialCropRegion)
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [showCropOverlay, setShowCropOverlay] = useState(false)
  const [isManualCrop, setIsManualCrop] = useState(false)
  const [isSavingCrop, setIsSavingCrop] = useState(false)
  const [metadataLoading, setMetadataLoading] = useState(false)
  const [videoDiagnostics, setVideoDiagnostics] = useState<Record<string, unknown> | null>(null)
  const [videoAlerts, setVideoAlerts] = useState<string[]>([])
  const isDevEnv = process.env.NODE_ENV !== 'production'
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080'

  const addVideoAlert = useCallback((message: string) => {
    setVideoAlerts(prev => (prev.includes(message) ? prev : [...prev, message]))
  }, [])

  // Timeline drag state
  const [isDraggingBullet, setIsDraggingBullet] = useState(false)
  const [draggedBulletIndex, setDraggedBulletIndex] = useState<number | null>(null)
  const [dragOffset, setDragOffset] = useState(0)
  const timelineRef = useRef<HTMLDivElement>(null)
  
  // Video event handlers
  const handlePlayPause = async () => {
    if (!videoRef.current) return

    try {
      if (isPlaying) {
        videoRef.current.pause()
        setIsPlaying(false)
      } else {
        await videoRef.current.play()
        setIsPlaying(true)
      }
    } catch (error) {
      console.error('[VideoPreview] Play/pause error:', error)
      addVideoAlert('Browser blocked video playback. Try clicking the video, then press Play again.')
    }
  }

  const handleTimeUpdate = () => {
    if (!videoRef.current) return
    setCurrentTime(videoRef.current.currentTime)
  }

  // Video metadata analysis
  const analyzeVideoMetadata = useCallback(async () => {
    if (!jobId) return

    setMetadataLoading(true)

    try {
      console.log('[VideoPreview] Analyzing video metadata via backend...')
      const response = await fetch(`${apiBaseUrl}/api/video/metadata/${jobId}`)

      if (response.ok) {
        const metadata = await response.json()
        const normalized = metadata as Record<string, any>
        console.log('[VideoPreview] Backend video metadata:', normalized)
        setVideoDiagnostics(normalized)

        const alerts: string[] = []
        const hasVideo = normalized?.raw_summary?.has_video ?? normalized?.stream_summary?.has_video

        if (!hasVideo) {
          alerts.push('Uploaded media contains no video frames. Preview will play audio only.')
        } else if (normalized?.used_preview_file) {
          const codec = normalized?.source_codec || normalized?.raw_summary?.video_codec || 'unknown codec'
          const container = normalized?.source_major_brand || normalized?.source_format_name || 'original container'
          alerts.push(`Preview converted to H.264 for browser compatibility (original ${codec}, container ${container}).`)
        }

        if (normalized?.stream_summary?.transcode_error) {
          alerts.push('Preview conversion failed; streaming original file. Codec issues may persist.')
        }

        setVideoAlerts(alerts)
      } else {
        console.warn('[VideoPreview] Could not fetch video metadata from backend:', response.status)
        setVideoDiagnostics(null)
        setVideoAlerts([`Metadata analysis request failed (${response.status})`])
      }
    } catch (error) {
      console.error('[VideoPreview] Video metadata analysis error:', error)
      setVideoDiagnostics(null)
      setVideoAlerts([`Metadata analysis error: ${String(error)}`])
    } finally {
      setMetadataLoading(false)
    }
  }, [apiBaseUrl, jobId])

  const handleLoadedMetadata = () => {
    if (!videoRef.current) return
    const video = videoRef.current
    const videoDuration = video.duration
    setDuration(videoDuration)
    onDurationChange?.(videoDuration)

    console.log('[VideoPreview] Video metadata loaded:', {
      duration: videoDuration,
      videoSrc: video.src,
      videoWidth: video.videoWidth,
      videoHeight: video.videoHeight,
      hasVideoTracks: video.videoTracks?.length > 0,
      hasAudioTracks: video.audioTracks?.length > 0,
      networkState: video.networkState,
      readyState: video.readyState,
      bulletPointsCount: summary.bullet_points.length,
      currentSrc: video.currentSrc
    })

    // Check if video has visual content
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      console.warn('[VideoPreview] Video has no dimensions - may be audio-only or corrupted')
      addVideoAlert('Browser reports zero video dimensions. Verify the uploaded file includes a video track.')
    }
  }

  const handleSeek = (newTime: number[]) => {
    if (!videoRef.current) return
    videoRef.current.currentTime = newTime[0]
    setCurrentTime(newTime[0])
  }

  const handleVolumeChange = (newVolume: number[]) => {
    if (!videoRef.current) return
    const vol = newVolume[0] / 100
    videoRef.current.volume = vol
    setVolume(vol)
    setIsMuted(vol === 0)
  }

  const toggleMute = () => {
    if (!videoRef.current) return
    const newMuted = !isMuted
    videoRef.current.muted = newMuted
    setIsMuted(newMuted)
  }

  // Video error handling
  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    const video = e.currentTarget
    const error = video.error

    console.error('[VideoPreview] Video error:', {
      errorCode: error?.code,
      errorMessage: error?.message,
      videoSrc: video.src,
      networkState: video.networkState,
      readyState: video.readyState
    })

    // Log detailed error information
    if (error) {
      const errorMessages = {
        1: "MEDIA_ERR_ABORTED - The user aborted the video loading",
        2: "MEDIA_ERR_NETWORK - A network error occurred while loading the video",
        3: "MEDIA_ERR_DECODE - An error occurred while decoding the video",
        4: "MEDIA_ERR_SRC_NOT_SUPPORTED - The video format is not supported"
      }
      const friendlyMessage = errorMessages[error.code as keyof typeof errorMessages] || 'Unknown error'
      console.error(`[VideoPreview] ${friendlyMessage}`)
      addVideoAlert(`Video playback error: ${friendlyMessage}`)
    }
  }

  const handleVideoLoad = () => {
    console.log('[VideoPreview] Video load event triggered')
  }

  const handleVideoLoadStart = () => {
    console.log('[VideoPreview] Video load start:', {
      src: videoRef.current?.src,
      networkState: videoRef.current?.networkState,
      readyState: videoRef.current?.readyState
    })
  }

  const handleVideoPlay = () => {
    console.log('[VideoPreview] Video play started:', {
      currentTime: videoRef.current?.currentTime,
      videoWidth: videoRef.current?.videoWidth,
      videoHeight: videoRef.current?.videoHeight,
      paused: videoRef.current?.paused
    })
  }

  const handleVideoCanPlay = () => {
    const video = videoRef.current
    if (!video) return

    console.log('[VideoPreview] Video can play:', {
      videoWidth: video.videoWidth,
      videoHeight: video.videoHeight,
      duration: video.duration,
      readyState: video.readyState,
      currentSrc: video.currentSrc,
      muted: video.muted,
      volume: video.volume,
      poster: video.poster
    })

    // Test if video is rendering by trying to draw a frame to canvas
    try {
      if (canvasRef.current && video.videoWidth > 0 && video.videoHeight > 0) {
        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')

        if (ctx) {
          canvas.width = video.videoWidth
          canvas.height = video.videoHeight

          try {
            ctx.drawImage(video, 0, 0)
            const sampleWidth = Math.min(video.videoWidth, 10)
            const sampleHeight = Math.min(video.videoHeight, 10)

            let hasNonBlackPixels = false
            let avgBrightness = 0
            let pixelData: number[] = []

            try {
              const imageData = ctx.getImageData(0, 0, sampleWidth, sampleHeight)
              pixelData = Array.from(imageData.data)
              hasNonBlackPixels = pixelData.some(pixel => pixel > 0)
              avgBrightness = pixelData.length > 0
                ? pixelData.reduce((sum, pixel) => sum + pixel, 0) / pixelData.length
                : 0
            } catch (imageDataError) {
              console.warn('[VideoPreview] Canvas getImageData failed (likely CORS):', imageDataError)
              // Skip pixel analysis but continue with video debugging
              hasNonBlackPixels = true // Assume video has content
              avgBrightness = 128 // Assume reasonable brightness
            }

            console.log('[VideoPreview] Video frame test:', {
              hasNonBlackPixels,
              avgBrightness: Math.round(avgBrightness * 100) / 100,
              samplePixels: pixelData.slice(0, 12),
              totalPixels: Math.floor(pixelData.length / 4),
              canvasSize: `${canvas.width}x${canvas.height}`,
              corsError: pixelData.length === 0
            })

            // Additional test: Try to extract a data URL
            try {
              const dataURL = canvas.toDataURL('image/jpeg', 0.1)
              console.log('[VideoPreview] Canvas data URL length:', dataURL.length)
            } catch (dataUrlError) {
              console.error('[VideoPreview] Canvas data URL error:', dataUrlError)
            }
          } catch (canvasError) {
            console.error('[VideoPreview] Canvas draw error:', canvasError)
          }
        } else {
          console.warn('[VideoPreview] Cannot get canvas context')
        }
      } else {
        console.warn('[VideoPreview] Cannot test video frame - no canvas or invalid video dimensions')
      }
    } catch (error) {
      console.error('[VideoPreview] Frame testing error:', error)
    }
  }

  // Timeline drag handlers
  const handleBulletMouseDown = (e: React.MouseEvent, index: number) => {
    e.preventDefault()
    e.stopPropagation()

    if (!timelineRef.current) return

    const rect = timelineRef.current.getBoundingClientRect()
    const bullet = summary.bullet_points[index]
    const [minutes, seconds] = bullet.timestamp.split(':').map(Number)
    const bulletTime = minutes * 60 + seconds
    const bulletPosition = duration > 0 ? (bulletTime / duration) * rect.width : 0

    setIsDraggingBullet(true)
    setDraggedBulletIndex(index)
    setDragOffset(e.clientX - rect.left - bulletPosition)
  }

  const handleTimelineMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingBullet || draggedBulletIndex === null || !timelineRef.current) return

    const rect = timelineRef.current.getBoundingClientRect()
    const newPosition = e.clientX - rect.left - dragOffset
    let newTime = Math.max(0, Math.min((newPosition / rect.width) * duration, duration))

    // Collision detection - prevent overlapping with other markers
    const markerWidthSeconds = 30 / rect.width * duration // Convert pixel width to seconds
    const minSpacing = markerWidthSeconds * 1.2 // 20% extra spacing

    summary.bullet_points.forEach((bullet, index) => {
      if (index === draggedBulletIndex) return // Skip the dragged bullet

      const [minutes, seconds] = bullet.timestamp.split(':').map(Number)
      const bulletTime = minutes * 60 + seconds

      // Check if too close to existing marker
      if (Math.abs(newTime - bulletTime) < minSpacing) {
        // Push to safer position
        if (newTime < bulletTime) {
          newTime = bulletTime - minSpacing
        } else {
          newTime = bulletTime + minSpacing
        }
        // Ensure still within bounds
        newTime = Math.max(0, Math.min(newTime, duration))
      }
    })

    // Update bullet timestamp
    const newTimestamp = formatTimeToTimestamp(newTime)
    const updatedBullets = [...summary.bullet_points]
    updatedBullets[draggedBulletIndex] = {
      ...updatedBullets[draggedBulletIndex],
      timestamp: newTimestamp
    }

    // Notify parent of changes (this will trigger automatic reordering)
    onBulletPointsChange?.(updatedBullets)
  }

  const handleTimelineMouseUp = () => {
    setIsDraggingBullet(false)
    setDraggedBulletIndex(null)
    setDragOffset(0)
  }

  // Enhanced format time helper for MM:SS format
  const formatTimeToTimestamp = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Crop region handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!isManualCrop || !containerRef.current) return
    
    const rect = containerRef.current.getBoundingClientRect()
    setIsDragging(true)
    setDragStart({
      x: e.clientX - rect.left - cropRegion.x,
      y: e.clientY - rect.top - cropRegion.y
    })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !containerRef.current) return
    
    const rect = containerRef.current.getBoundingClientRect()
    const newX = Math.max(0, Math.min(e.clientX - rect.left - dragStart.x, rect.width - cropRegion.width))
    const newY = Math.max(0, Math.min(e.clientY - rect.top - dragStart.y, rect.height - cropRegion.height))
    
    const newCropRegion = { ...cropRegion, x: newX, y: newY }
    setCropRegion(newCropRegion)
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const resetCropRegion = () => {
    setCropRegion(initialCropRegion)
    toast.info("Crop region reset to face detection")
  }

  const saveCropRegion = async () => {
    setIsSavingCrop(true)
    try {
      await updateCropRegion(jobId, cropRegion)
      onCropChange?.(cropRegion)
      toast.success("Crop region saved successfully")
    } catch (error) {
      console.error('Error saving crop region:', error)
      toast.error("Failed to save crop region")
    } finally {
      setIsSavingCrop(false)
    }
  }

  // Format time helper
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Get bullet point at current time
  const getCurrentBulletPoint = () => {
    return summary.bullet_points.find(bullet => {
      const [minutes, seconds] = bullet.timestamp.split(':').map(Number)
      const bulletTime = minutes * 60 + seconds
      return Math.abs(currentTime - bulletTime) <= bullet.duration / 2
    })
  }

  const currentBullet = getCurrentBulletPoint()

  // Debug logging for props changes
  useEffect(() => {
    console.log('[VideoPreview] Props changed:', {
      videoUrl,
      bulletPointsCount: summary.bullet_points.length,
      duration,
      bulletPoints: summary.bullet_points
    })
  }, [videoUrl, summary.bullet_points, duration])

  useEffect(() => {
    setVideoAlerts([])
    setVideoDiagnostics(null)
    if (!jobId) return
    void analyzeVideoMetadata()
  }, [jobId, videoUrl, analyzeVideoMetadata])

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <VideoIcon className="w-5 h-5 text-blue-600" />
              Video Preview & Crop Adjustment
            </CardTitle>
            <CardDescription>
              Preview your video and adjust the face crop region for final composition
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-green-100 text-green-800">
              Face detected: {Math.round(faceDetectionConfidence * 100)}%
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {videoAlerts.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-amber-900 space-y-2">
            {videoAlerts.map((alert, index) => (
              <div key={index} className="flex items-start gap-2 text-sm">
                <AlertTriangle className="w-4 h-4 mt-0.5 text-amber-600" />
                <span>{alert}</span>
              </div>
            ))}
          </div>
        )}

        {metadataLoading && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Analyzing video metadata…</span>
          </div>
        )}

        {isDevEnv && videoDiagnostics && (
          <details className="bg-gray-50 border border-gray-200 rounded p-3 text-xs text-gray-700">
            <summary className="cursor-pointer select-none mb-1 font-medium">Preview diagnostics</summary>
            <pre className="whitespace-pre-wrap break-words text-[11px]">{JSON.stringify(videoDiagnostics, null, 2)}</pre>
          </details>
        )}

        {/* Video Player Container */}
        <div 
          ref={containerRef}
          className="relative bg-black rounded-lg overflow-hidden"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <video
            ref={videoRef}
            src={videoUrl}
            crossOrigin="anonymous"
            className="w-full h-auto"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onPlay={() => {
              setIsPlaying(true)
              handleVideoPlay()
            }}
            onPause={() => setIsPlaying(false)}
            onError={handleVideoError}
            onLoad={handleVideoLoad}
            onLoadStart={handleVideoLoadStart}
            onCanPlay={handleVideoCanPlay}
            playsInline
            preload="metadata"
            controls={false}
            muted={isMuted}
          />

          {/* Hidden canvas for video frame testing */}
          <canvas
            ref={canvasRef}
            style={{ display: 'none' }}
            width="1"
            height="1"
          />

          {/* Crop Overlay */}
          {showCropOverlay && (
            <>
              {/* Dark overlay areas */}
              <div className="absolute inset-0 bg-black bg-opacity-50 pointer-events-none" />
              
              {/* Crop window */}
              <div
                className={cn(
                  "absolute border-2 border-blue-400 bg-transparent",
                  isManualCrop && "cursor-move",
                  isDragging && "border-blue-600"
                )}
                style={{
                  left: `${(cropRegion.x / (containerRef.current?.clientWidth || 1)) * 100}%`,
                  top: `${(cropRegion.y / (containerRef.current?.clientHeight || 1)) * 100}%`,
                  width: `${(cropRegion.width / (containerRef.current?.clientWidth || 1)) * 100}%`,
                  height: `${(cropRegion.height / (containerRef.current?.clientHeight || 1)) * 100}%`
                }}
                onMouseDown={handleMouseDown}
              >
                {/* Crop corners for visual feedback */}
                <div className="absolute -top-1 -left-1 w-2 h-2 bg-blue-400 rounded-full" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-blue-400 rounded-full" />
                <div className="absolute -bottom-1 -left-1 w-2 h-2 bg-blue-400 rounded-full" />
                <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-blue-400 rounded-full" />
                
                {/* Move icon when hovering */}
                {isManualCrop && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="bg-blue-600 text-white p-2 rounded-full opacity-75">
                      <Move className="w-4 h-4" />
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Video Controls Overlay */}
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            <div className="flex items-center gap-3">
              <Button
                size="sm"
                variant="ghost"
                onClick={handlePlayPause}
                className="text-white hover:bg-white/20"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </Button>

              <div className="flex-1">
                <Slider
                  value={[currentTime]}
                  max={duration}
                  step={0.1}
                  onValueChange={handleSeek}
                  className="w-full"
                />
              </div>

              <span className="text-white text-sm font-mono">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>

              <Button
                size="sm"
                variant="ghost"
                onClick={toggleMute}
                className="text-white hover:bg-white/20"
              >
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </Button>

              <div className="w-24">
                <Slider
                  value={[volume * 100]}
                  max={100}
                  step={1}
                  onValueChange={handleVolumeChange}
                  className="w-full"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Bullet Point Timeline */}
        {summary.bullet_points.length > 0 && (
          <div className="space-y-2">
            <Label className="text-sm font-medium">
              Bullet Point Timeline
              <span className="text-xs text-gray-500 ml-2">(Click to seek • Drag to reorder)</span>
            </Label>
            {/* Debug info - only show if needed */}
            {process.env.NODE_ENV === 'development' && (
              <div className="text-xs text-gray-400 bg-gray-50 p-2 rounded">
                Debug: {summary.bullet_points.length} bullets • Duration: {duration.toFixed(1)}s •
                Current: {currentTime.toFixed(1)}s
              </div>
            )}
            <div
              ref={timelineRef}
              className="relative h-8 bg-gray-100 rounded cursor-crosshair"
              onMouseMove={handleTimelineMouseMove}
              onMouseUp={handleTimelineMouseUp}
              onMouseLeave={handleTimelineMouseUp}
            >
              {summary.bullet_points.map((bullet, index) => {
                const [minutes, seconds] = bullet.timestamp.split(':').map(Number)
                const bulletTime = minutes * 60 + seconds
                const left = duration > 0 ? (bulletTime / duration) * 100 : 0
                // Fixed width for markers - just enough space for the number
                const markerWidth = 30 // pixels, not percentage
                const isCurrentBullet = currentBullet?.timestamp === bullet.timestamp
                const isDraggedBullet = draggedBulletIndex === index

                // Debug logging for timeline markers
                if (index === 0) {
                  console.log('[VideoPreview] Timeline bullet calculations:', {
                    bulletCount: summary.bullet_points.length,
                    videoDuration: duration,
                    firstBullet: {
                      timestamp: bullet.timestamp,
                      bulletTime,
                      left: `${left}%`,
                      width: `${markerWidth}px`
                    }
                  })
                }

                return (
                  <div
                    key={`${bullet.timestamp}-${index}`}
                    className={cn(
                      "absolute top-1 h-6 border-2 rounded text-xs flex items-center justify-center select-none transition-all duration-200",
                      isCurrentBullet
                        ? "bg-blue-400 border-blue-500 text-white shadow-md"
                        : "bg-blue-200 border-blue-300 text-blue-900",
                      isDraggedBullet && "cursor-grabbing shadow-lg scale-110 border-blue-600",
                      !isDraggedBullet && "cursor-grab hover:bg-blue-300 hover:border-blue-400 hover:shadow-sm"
                    )}
                    style={{
                      left: `calc(${left}% - ${markerWidth/2}px)`,
                      width: `${markerWidth}px`,
                      // Higher z-index for dragged, current, and hovered markers
                      zIndex: isDraggedBullet ? 100 : isCurrentBullet ? 50 : 20 + index
                    }}
                    onMouseDown={(e) => handleBulletMouseDown(e, index)}
                    onClick={() => !isDraggingBullet && handleSeek([bulletTime])}
                    title={`${bullet.timestamp}: ${bullet.text}`}
                    onMouseEnter={(e) => {
                      // Temporarily raise z-index on hover to make marker visible
                      if (!isDraggingBullet) {
                        e.currentTarget.style.zIndex = '60'
                      }
                    }}
                    onMouseLeave={(e) => {
                      // Reset z-index when not hovering
                      if (!isDraggingBullet) {
                        e.currentTarget.style.zIndex = isCurrentBullet ? '50' : `${20 + index}`
                      }
                    }}
                  >
                    <span className="font-medium text-xs">{index + 1}</span>
                  </div>
                )
              })}

              {/* Visual feedback during drag */}
              {isDraggingBullet && (
                <div className="absolute inset-0 bg-blue-50 bg-opacity-50 rounded border-2 border-dashed border-blue-300">
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-xs text-blue-600 font-medium">
                    Drag to reorder • Release to place
                  </div>
                </div>
              )}
            </div>

            {currentBullet && (
              <div className="text-sm text-gray-600">
                <Badge variant="outline" className="mr-2">{currentBullet.timestamp}</Badge>
                {currentBullet.text}
              </div>
            )}
          </div>
        )}

        {/* Crop Controls */}
        <div className="space-y-4 border-t pt-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label className="text-sm font-medium">Crop Region Controls</Label>
              <p className="text-xs text-gray-500">
                Adjust how the speaker's face will appear in the final video
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="manual-crop" className="text-sm">Manual adjustment</Label>
              <Switch
                id="manual-crop"
                checked={isManualCrop}
                onCheckedChange={setIsManualCrop}
              />
            </div>
          </div>

          {/* Crop Region Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <Label className="text-xs text-gray-500">X Position</Label>
              <div className="font-mono">{Math.round(cropRegion.x)}px</div>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Y Position</Label>
              <div className="font-mono">{Math.round(cropRegion.y)}px</div>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Width</Label>
              <div className="font-mono">{Math.round(cropRegion.width)}px</div>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Height</Label>
              <div className="font-mono">{Math.round(cropRegion.height)}px</div>
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Switch
                id="show-overlay"
                checked={showCropOverlay}
                onCheckedChange={setShowCropOverlay}
              />
              <Label htmlFor="show-overlay" className="text-sm">
                Show crop overlay
              </Label>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={resetCropRegion}
                disabled={!isManualCrop}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset
              </Button>
              <Button
                size="sm"
                onClick={saveCropRegion}
                disabled={isSavingCrop || !isManualCrop}
              >
                {isSavingCrop ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Crop
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Instructions */}
          <div className="text-xs text-gray-500 bg-gray-50 rounded p-3">
            <p className="font-medium mb-1">How to adjust crop region:</p>
            <ul className="space-y-1">
              <li>• Enable "Manual adjustment" to modify the crop region</li>
              <li>• Click and drag the blue rectangle to reposition</li>
              <li>• The crop region shows where the speaker will appear in the final 50/50 layout</li>
              <li>• Save your changes to apply them to the final video generation</li>
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
