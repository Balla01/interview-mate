import { useRef, useState, useCallback } from 'react'

const SAMPLE_RATE = 16000
const BUFFER_SIZE = 4096

function float32ToInt16WithChannel(float32, channel) {
  // Binary format: byte[0]=channel, byte[1..]=PCM Int16 LE
  const int16 = new Int16Array(float32.length)
  for (let i = 0; i < float32.length; i++) {
    int16[i] = Math.max(-32768, Math.min(32767, float32[i] * 32768))
  }
  const out = new Uint8Array(1 + int16.byteLength)
  out[0] = channel
  out.set(new Uint8Array(int16.buffer), 1)
  return out.buffer
}

function buildProcessor(stream, channel, onChunk) {
  const ctx = new AudioContext({ sampleRate: SAMPLE_RATE })
  const source = ctx.createMediaStreamSource(stream)
  // ScriptProcessorNode is deprecated but universally supported
  const processor = ctx.createScriptProcessor(BUFFER_SIZE, 1, 1)
  processor.onaudioprocess = (e) => {
    onChunk(float32ToInt16WithChannel(e.inputBuffer.getChannelData(0), channel))
  }
  source.connect(processor)
  processor.connect(ctx.destination)
  return { ctx, processor, source }
}

export function useAudio(onChunk) {
  const [micActive, setMicActive] = useState(false)
  const [sysActive, setSysActive] = useState(false)
  const [error, setError] = useState(null)

  const micRef = useRef(null)
  const sysRef = useRef(null)

  const startMic = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true },
      })
      micRef.current = buildProcessor(stream, 0, onChunk)
      micRef.current.stream = stream
      setMicActive(true)
    } catch (err) {
      setError(`Microphone: ${err.message}`)
    }
  }, [onChunk])

  const startSystemAudio = useCallback(async () => {
    try {
      setError(null)
      // getDisplayMedia captures tab/window/screen audio
      const stream = await navigator.mediaDevices.getDisplayMedia({
        audio: true,
        video: { width: 1, height: 1 },
      })
      // Drop the video track immediately — we only need audio
      stream.getVideoTracks().forEach(t => t.stop())
      const audioTracks = stream.getAudioTracks()
      if (!audioTracks.length) {
        throw new Error('No audio track — make sure to check "Share audio" in the prompt')
      }
      const audioStream = new MediaStream(audioTracks)
      sysRef.current = buildProcessor(audioStream, 1, onChunk)
      sysRef.current.stream = audioStream
      // Auto-stop when user ends screen share
      audioTracks[0].addEventListener('ended', stopSystemAudio)
      setSysActive(true)
    } catch (err) {
      setError(`System audio: ${err.message}`)
    }
  }, [onChunk])

  const stopMic = useCallback(() => {
    if (micRef.current) {
      micRef.current.processor?.disconnect()
      micRef.current.ctx?.close()
      micRef.current.stream?.getTracks().forEach(t => t.stop())
      micRef.current = null
    }
    setMicActive(false)
  }, [])

  const stopSystemAudio = useCallback(() => {
    if (sysRef.current) {
      sysRef.current.processor?.disconnect()
      sysRef.current.ctx?.close()
      sysRef.current.stream?.getTracks().forEach(t => t.stop())
      sysRef.current = null
    }
    setSysActive(false)
  }, [])

  const stopAll = useCallback(() => {
    stopMic()
    stopSystemAudio()
  }, [stopMic, stopSystemAudio])

  return { micActive, sysActive, error, startMic, startSystemAudio, stopAll }
}
