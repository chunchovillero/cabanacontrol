import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { assistantApi } from './api'

export function VoiceRecorder({
  tenant,
  onText,
}: {
  tenant: string
  onText: (text: string) => void
}) {
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const mounted = useRef(true)
  const starting = useRef(false)
  const [recording, setRecording] = useState(false)
  const [audio, setAudio] = useState<Blob | null>(null)
  const [preview, setPreview] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const supported = typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getUserMedia
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      clearTimeout(timer.current)
      if (recorder.current?.state === 'recording') recorder.current.stop()
      stream.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])
  useEffect(() => {
    if (!audio) {
      setPreview('')
      return
    }
    const url = URL.createObjectURL(audio)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [audio])
  async function start() {
    if (starting.current || recording) return
    starting.current = true
    setError('')
    setAudio(null)
    setReviewed(false)
    try {
      const current = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!mounted.current) {
        current.getTracks().forEach((track) => track.stop())
        return
      }
      stream.current = current
      const mime = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find((type) =>
        MediaRecorder.isTypeSupported(type),
      )
      if (!mime) throw new Error('Formato no compatible. Escribe el resumen.')
      const active = new MediaRecorder(current, { mimeType: mime })
      recorder.current = active
      const chunks: Blob[] = []
      let size = 0
      active.ondataavailable = (event) => {
        size += event.data.size
        if (size <= 5 * 1024 * 1024) chunks.push(event.data)
        else if (active.state === 'recording') active.stop()
      }
      active.onstop = () => {
        clearTimeout(timer.current)
        current.getTracks().forEach((track) => track.stop())
        if (!mounted.current) return
        setRecording(false)
        if (size > 5 * 1024 * 1024) setError('Audio superior a 5 MB. Escribe el resumen.')
        else setAudio(new Blob(chunks, { type: mime }))
      }
      active.start(500)
      setRecording(true)
      timer.current = setTimeout(() => {
        if (active.state === 'recording') active.stop()
      }, 59000)
    } catch (failure) {
      stream.current?.getTracks().forEach((track) => track.stop())
      setError(
        failure instanceof Error
          ? failure.message
          : 'No se pudo usar el micrófono. Escribe el resumen.',
      )
    } finally {
      starting.current = false
    }
  }
  async function send() {
    if (!audio || !reviewed) return
    setBusy(true)
    setError('')
    try {
      const result = await assistantApi.transcribe(tenant, audio)
      if (mounted.current) {
        onText(result.text)
        setAudio(null)
        setReviewed(false)
      }
    } catch (failure) {
      if (mounted.current)
        setError(
          failure instanceof Error
            ? failure.message
            : 'No se pudo transcribir. Escribe el resumen.',
        )
    } finally {
      if (mounted.current) setBusy(false)
    }
  }
  return (
    <fieldset className="space-y-3 rounded-xl border p-4">
      <legend className="px-2 font-medium">Dictado voluntario</legend>
      <p className="text-sm">
        Dicta tu resumen sin datos personales. Máximo 60 segundos y 5 MB. No grabes llamadas ni a
        terceros. Revisa el audio antes de enviarlo a OpenAI.
      </p>
      {!supported ? (
        <p>Tu navegador no permite dictado. Puedes escribir o pegar el texto.</p>
      ) : (
        <div className="flex flex-wrap gap-3">
          <Button
            type="button"
            variant="outline"
            disabled={recording || busy}
            onClick={() => {
              void start()
            }}
          >
            Iniciar dictado
          </Button>
          {recording && (
            <Button type="button" onClick={() => recorder.current?.stop()}>
              Detener dictado
            </Button>
          )}
        </div>
      )}
      {recording && <p role="status">Grabando · parada automática antes de 60 segundos</p>}
      {audio && (
        <div className="space-y-3">
          {preview && (
            <audio controls src={preview} aria-label="Revisar dictado" className="max-w-full" />
          )}
          <label className="flex gap-3">
            <input
              type="checkbox"
              checked={reviewed}
              onChange={(event) => setReviewed(event.target.checked)}
            />
            Revisé el audio y autorizo enviarlo a OpenAI para transcribir.
          </label>
          <Button
            type="button"
            disabled={busy || !reviewed}
            onClick={() => {
              void send()
            }}
          >
            {busy ? 'Transcribiendo…' : 'Enviar a transcribir'}
          </Button>
          <Button type="button" variant="outline" disabled={busy} onClick={() => setAudio(null)}>
            Descartar dictado
          </Button>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </fieldset>
  )
}
