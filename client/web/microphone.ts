import { CONFIG } from "../config";

export interface MicrophoneOptions {
  onAudioChunk: (chunk: Float32Array, timestamp: number) => void;
  onSilence: (audioBuffer: Float32Array) => void;
  onError: (error: Error) => void;
}

export class MicrophoneCapture {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private analyserNode: AnalyserNode | null = null;
  private isRecording = false;
  private silenceTimer: ReturnType<typeof setTimeout> | null = null;
  private audioBuffer: Float32Array[] = [];
  private options: MicrophoneOptions;

  constructor(options: MicrophoneOptions) {
    this.options = options;
  }

  async start(): Promise<void> {
    if (this.isRecording) return;

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: CONFIG.AUDIO.CHANNELS,
          sampleRate: CONFIG.AUDIO.SAMPLE_RATE,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this.audioContext = new AudioContext({ sampleRate: CONFIG.AUDIO.SAMPLE_RATE });
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Analyser for silence detection
      this.analyserNode = this.audioContext.createAnalyser();
      this.analyserNode.fftSize = 512;

      // ScriptProcessor for raw PCM data
      this.processorNode = this.audioContext.createScriptProcessor(
        CONFIG.AUDIO.CHUNK_SIZE,
        1,
        1
      );

      this.processorNode.onaudioprocess = (event) => {
        if (!this.isRecording) return;

        const inputData = event.inputBuffer.getChannelData(0);
        const chunk = new Float32Array(inputData);
        const timestamp = Date.now();

        // Accumulate buffer
        this.audioBuffer.push(chunk);

        // Emit chunk for streaming
        this.options.onAudioChunk(chunk, timestamp);

        // Silence detection
        const rms = this.calculateRMS(chunk);
        if (rms < CONFIG.AUDIO.SILENCE_THRESHOLD) {
          if (!this.silenceTimer) {
            this.silenceTimer = setTimeout(() => {
              this.flushBuffer();
            }, CONFIG.AUDIO.SILENCE_DURATION_MS);
          }
        } else {
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
          }
        }
      };

      this.sourceNode.connect(this.analyserNode);
      this.analyserNode.connect(this.processorNode);
      this.processorNode.connect(this.audioContext.destination);

      this.isRecording = true;
    } catch (error) {
      this.options.onError(error as Error);
      throw error;
    }
  }

  private calculateRMS(buffer: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < buffer.length; i++) {
      sum += buffer[i] * buffer[i];
    }
    return Math.sqrt(sum / buffer.length);
  }

  private flushBuffer(): void {
    if (this.audioBuffer.length === 0) return;

    // Merge all chunks
    const totalLength = this.audioBuffer.reduce((acc, chunk) => acc + chunk.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.audioBuffer) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    this.audioBuffer = [];
    this.options.onSilence(merged);
  }

  stop(): void {
    this.isRecording = false;

    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }

    this.flushBuffer();

    if (this.processorNode) {
      this.processorNode.disconnect();
      this.processorNode = null;
    }
    if (this.analyserNode) {
      this.analyserNode.disconnect();
      this.analyserNode = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }

  /**
   * Convert Float32Array PCM to Int16 PCM for transmission
   */
  static float32ToInt16(buffer: Float32Array): Int16Array {
    const out = new Int16Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
      const s = Math.max(-1, Math.min(1, buffer[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }

  get recording(): boolean {
    return this.isRecording;
  }
}
