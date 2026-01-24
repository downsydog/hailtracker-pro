/**
 * Radar Replay Component
 * Frame-by-frame radar playback with controls
 */

import { useState, useEffect, useCallback, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
  Radio,
  RefreshCw,
} from "lucide-react"
import { stormMonitorApi, RadarSite } from "@/api/weather"

interface RadarReplayProps {
  defaultRadarId?: string
  onFrameChange?: (frame: { timestamp: string; index: number }) => void
  className?: string
}

export function RadarReplay({
  defaultRadarId = "KFWS",
  onFrameChange,
  className = "",
}: RadarReplayProps) {
  const [selectedRadar, setSelectedRadar] = useState(defaultRadarId)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0)
  const [playbackSpeed, setPlaybackSpeed] = useState(500) // ms per frame
  const playbackRef = useRef<NodeJS.Timeout | null>(null)

  // Fetch available radars
  const { data: radarsData } = useQuery({
    queryKey: ["radar-sites"],
    queryFn: () => stormMonitorApi.getAvailableRadars(),
  })

  const radars: RadarSite[] = radarsData?.data?.radars || []

  // Fetch radar history
  const {
    data: historyData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["radar-history", selectedRadar],
    queryFn: () =>
      stormMonitorApi.getRadarHistory({
        radar_id: selectedRadar,
      }),
    enabled: !!selectedRadar,
  })

  const frames = historyData?.data?.frames || []
  const frameCount = frames.length

  // Handle playback
  useEffect(() => {
    if (isPlaying && frameCount > 0) {
      playbackRef.current = setInterval(() => {
        setCurrentFrameIndex((prev) => {
          const next = (prev + 1) % frameCount
          return next
        })
      }, playbackSpeed)
    }

    return () => {
      if (playbackRef.current) {
        clearInterval(playbackRef.current)
      }
    }
  }, [isPlaying, frameCount, playbackSpeed])

  // Notify parent of frame changes
  useEffect(() => {
    if (frames[currentFrameIndex] && onFrameChange) {
      onFrameChange({
        timestamp: frames[currentFrameIndex].timestamp,
        index: currentFrameIndex,
      })
    }
  }, [currentFrameIndex, frames, onFrameChange])

  const togglePlayback = useCallback(() => {
    setIsPlaying((prev) => !prev)
  }, [])

  const goToFrame = useCallback((index: number) => {
    setCurrentFrameIndex(Math.max(0, Math.min(index, frameCount - 1)))
  }, [frameCount])

  const stepForward = useCallback(() => {
    setCurrentFrameIndex((prev) => Math.min(prev + 1, frameCount - 1))
  }, [frameCount])

  const stepBackward = useCallback(() => {
    setCurrentFrameIndex((prev) => Math.max(prev - 1, 0))
  }, [])

  const goToStart = useCallback(() => {
    setCurrentFrameIndex(0)
    setIsPlaying(false)
  }, [])

  const goToEnd = useCallback(() => {
    setCurrentFrameIndex(frameCount - 1)
    setIsPlaying(false)
  }, [frameCount])

  const currentFrame = frames[currentFrameIndex]
  const currentTime = currentFrame
    ? new Date(currentFrame.timestamp).toLocaleTimeString()
    : "--:--"

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Radio className="h-5 w-5 text-blue-500" />
            Radar Replay
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw
              className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
            />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Radar Selection */}
        <div className="flex items-center gap-2">
          <Select value={selectedRadar} onValueChange={setSelectedRadar}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select radar" />
            </SelectTrigger>
            <SelectContent>
              {radars.map((radar) => (
                <SelectItem key={radar.site_code} value={radar.site_code}>
                  {radar.site_code} - {radar.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={String(playbackSpeed)}
            onValueChange={(v) => setPlaybackSpeed(parseInt(v))}
          >
            <SelectTrigger className="w-[100px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1000">0.5x</SelectItem>
              <SelectItem value="500">1x</SelectItem>
              <SelectItem value="250">2x</SelectItem>
              <SelectItem value="100">5x</SelectItem>
            </SelectContent>
          </Select>

          <Badge variant="outline">{frameCount} frames</Badge>
        </div>

        {/* Frame Display */}
        {isLoading ? (
          <div className="h-[300px] bg-muted rounded-lg flex items-center justify-center">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : currentFrame ? (
          <div className="relative h-[300px] bg-muted rounded-lg overflow-hidden">
            {/* Use the IEM tile layer or NWS image */}
            <img
              src={currentFrame.image_url}
              alt={`Radar frame ${currentFrameIndex + 1}`}
              className="w-full h-full object-contain"
              onError={(e) => {
                // Fallback to a placeholder if image fails
                (e.target as HTMLImageElement).src =
                  "https://radar.weather.gov/ridge/standard/CONUS-LARGE_0.gif"
              }}
            />
            {/* Timestamp overlay */}
            <div className="absolute bottom-2 left-2 bg-black/70 text-white px-2 py-1 rounded text-sm">
              {currentTime}
            </div>
            <div className="absolute bottom-2 right-2 bg-black/70 text-white px-2 py-1 rounded text-sm">
              Frame {currentFrameIndex + 1} / {frameCount}
            </div>
          </div>
        ) : (
          <div className="h-[300px] bg-muted rounded-lg flex items-center justify-center text-muted-foreground">
            No radar data available
          </div>
        )}

        {/* Playback Controls */}
        <div className="space-y-3">
          {/* Timeline Slider */}
          <Slider
            value={[currentFrameIndex]}
            onValueChange={([value]) => goToFrame(value)}
            max={Math.max(0, frameCount - 1)}
            step={1}
            className="cursor-pointer"
          />

          {/* Control Buttons */}
          <div className="flex items-center justify-center gap-2">
            <Button variant="outline" size="icon" onClick={goToStart}>
              <SkipBack className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={stepBackward}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              size="icon"
              onClick={togglePlayback}
              className={isPlaying ? "bg-orange-500 hover:bg-orange-600" : ""}
            >
              {isPlaying ? (
                <Pause className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </Button>
            <Button variant="outline" size="icon" onClick={stepForward}>
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={goToEnd}>
              <SkipForward className="h-4 w-4" />
            </Button>
          </div>

          {/* Time Range */}
          {historyData?.data && (
            <div className="text-xs text-center text-muted-foreground">
              {new Date(historyData.data.start_time).toLocaleString()} -{" "}
              {new Date(historyData.data.end_time).toLocaleString()}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default RadarReplay
