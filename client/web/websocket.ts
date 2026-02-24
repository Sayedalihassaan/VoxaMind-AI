import { CONFIG } from "../config";
import { MicrophoneCapture } from "./microphone";
import { AudioPlayer } from "./audio-player";

export type WSMessageType =
  | "audio_chunk"
  | "audio_end"
  | "transcript"
  | "response_text"
  | "response_audio"
  | "response_audio_end"
  | "error"
  | "ping"
  | "pong"
  | "session_start"
  | "session_end";

export interface WSMessage {
  type: WSMessageType;
  data?: unknown;
  session_id?: string;
  timestamp?: number;
}

export interface VoiceAgentCallbacks {
  onTranscript?: (text: string, isFinal: boolean) => void;
  onResponseText?: (text: string, isFinal: boolean) => void;
  onResponseAudio?: (audio: ArrayBuffer) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: string) => void;
  onStateChange?: (state: "idle" | "listening" | "processing" | "speaking") => void;
}

export class VoiceAgentWebSocket {
  private ws: WebSocket | null = null;
  private microphone: MicrophoneCapture | null = null;
  private audioPlayer: AudioPlayer;
  private callbacks: VoiceAgentCallbacks;
  private sessionId: string | null = null;
  private reconnectAttempts = 0;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private state: "idle" | "listening" | "processing" | "speaking" = "idle";

  constructor(callbacks: VoiceAgentCallbacks) {
    this.callbacks = callbacks;
    this.audioPlayer = new AudioPlayer({
      onPlaybackStart: () => this.setState("speaking"),
      onPlaybackEnd: () => this.setState("idle"),
    });
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(CONFIG.WS_URL);
      this.ws.binaryType = "arraybuffer";

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.startPing();
        this.callbacks.onConnected?.();
        resolve();
      };

      this.ws.onerror = (event) => {
        console.error("WebSocket error:", event);
        reject(new Error("WebSocket connection failed"));
      };

      this.ws.onclose = () => {
        this.stopPing();
        this.callbacks.onDisconnected?.();
        this.attemptReconnect();
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event);
      };
    });
  }

  private handleMessage(event: MessageEvent): void {
    // Binary = audio data
    if (event.data instanceof ArrayBuffer) {
      this.handleAudioChunk(event.data);
      return;
    }

    try {
      const message: WSMessage = JSON.parse(event.data);
      switch (message.type) {
        case "session_start":
          this.sessionId = (message.data as { session_id: string }).session_id;
          break;

        case "transcript":
          const transcriptData = message.data as { text: string; is_final: boolean };
          this.callbacks.onTranscript?.(transcriptData.text, transcriptData.is_final);
          if (transcriptData.is_final) this.setState("processing");
          break;

        case "response_text":
          const textData = message.data as { text: string; is_final: boolean };
          this.callbacks.onResponseText?.(textData.text, textData.is_final);
          break;

        case "response_audio":
          const audioData = message.data as { audio: string; sample_rate: number };
          const binary = atob(audioData.audio);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          this.audioPlayer.queueAudio(bytes.buffer, audioData.sample_rate);
          break;

        case "response_audio_end":
          // All audio has been queued
          break;

        case "error":
          this.callbacks.onError?.((message.data as { message: string }).message);
          this.setState("idle");
          break;

        case "pong":
          break;
      }
    } catch (error) {
      console.error("Failed to parse message:", error);
    }
  }

  private handleAudioChunk(data: ArrayBuffer): void {
    this.audioPlayer.queueAudio(data);
  }

  async startListening(): Promise<void> {
    await this.audioPlayer.resume();
    this.audioPlayer.stop(); // Stop any current playback

    this.microphone = new MicrophoneCapture({
      onAudioChunk: (chunk, timestamp) => {
        if (this.ws?.readyState !== WebSocket.OPEN) return;
        const int16 = MicrophoneCapture.float32ToInt16(chunk);
        this.sendBinary(int16.buffer);
      },
      onSilence: (audioBuffer) => {
        // Signal end of utterance
        this.sendJSON({ type: "audio_end", timestamp: Date.now() });
        this.setState("processing");
      },
      onError: (error) => {
        this.callbacks.onError?.(error.message);
      },
    });

    await this.microphone.start();
    this.setState("listening");
    this.sendJSON({ type: "session_start", data: { format: CONFIG.AUDIO.FORMAT, sample_rate: CONFIG.AUDIO.SAMPLE_RATE } });
  }

  stopListening(): void {
    this.microphone?.stop();
    this.microphone = null;
    if (this.state === "listening") {
      this.setState("idle");
    }
  }

  private sendJSON(message: WSMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private sendBinary(data: ArrayBuffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    }
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      this.sendJSON({ type: "ping", timestamp: Date.now() });
    }, 30000);
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private setState(state: typeof this.state): void {
    if (this.state !== state) {
      this.state = state;
      this.callbacks.onStateChange?.(state);
    }
  }

  private async attemptReconnect(): Promise<void> {
    if (this.reconnectAttempts >= CONFIG.MAX_RECONNECT_ATTEMPTS) return;
    this.reconnectAttempts++;
    await new Promise((r) => setTimeout(r, CONFIG.RECONNECT_DELAY_MS));
    try {
      await this.connect();
    } catch (_) {
      // Will retry via onclose
    }
  }

  disconnect(): void {
    this.stopPing();
    this.stopListening();
    this.ws?.close();
    this.ws = null;
  }

  get currentState() {
    return this.state;
  }
}
