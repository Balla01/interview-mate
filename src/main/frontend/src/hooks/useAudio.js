import { useRef, useState, useCallback } from 'react'

const SAMPLE_RATE = 16000
const BUFFER_SIZE = 4096

function buildProcessor(stream, channel, onChunk) {
  const ctx  = new AudioContext({ sampleRate: SAMPLE_RATE })
  const src  = ctx.createMediaStreamSource(stream)
  const proc = ctx.createScriptProcessor(BUFFER_SIZE, 1, 1)
  proc.onaudioprocess = e => {
    const f   = e.inputBuffer.getChannelData(0)
    const i16 = new Int16Array(f.length)
    for (let i = 0; i < f.length; i++) i16[i] = Math.max(-32768, Math.min(32767, f[i] * 32768))
    const out = new Uint8Array(1 + i16.byteLength)
    out[0] = channel
    out.set(new Uint8Array(i16.buffer), 1)
    onChunk(out.buffer)
  }
  src.connect(proc)
  proc.connect(ctx.destination)
  return { ctx, proc, src, stream }
}

export function useAudio(onChunk) {
  const [micActive, setMicActive] = useState(false)
  const [sysActive, setSysActive] = useState(false)
  const [audioError, setError]    = useState(null)
  const micRef = useRef(null)
  const sysRef = useRef(null)

  const startMic = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      })
      micRef.current = buildProcessor(stream, 0, onChunk)
      setMicActive(true)
    } catch (e) { setError('Microphone: ' + e.message) }
  }, [onChunk])

  const startSystemAudio = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getDisplayMedia({ audio: true, video: { width: 1, height: 1 } })
      stream.getVideoTracks().forEach(t => t.stop())
      const tracks = stream.getAudioTracks()
      if (!tracks.length) throw new Error('No audio — check "Share audio" in the browser prompt')
      sysRef.current = buildProcessor(new MediaStream(tracks), 1, onChunk)
      setSysActive(true)
      tracks[0].addEventListener('ended', () => { sysRef.current = null; setSysActive(false) })
    } catch (e) { setError('System audio: ' + e.message) }
  }, [onChunk])

  const stopAll = useCallback(() => {
    [micRef, sysRef].forEach(r => {
      if (!r.current) return
      try { r.current.proc.disconnect(); r.current.ctx.close(); r.current.stream.getTracks().forEach(t => t.stop()) } catch (_) {}
      r.current = null
    })
    setMicActive(false); setSysActive(false)
  }, [])

  return { micActive, sysActive, audioError, startMic, startSystemAudio, stopAll }
}
