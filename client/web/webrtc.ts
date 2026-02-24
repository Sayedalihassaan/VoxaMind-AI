import { CONFIG } from "../config";

export interface WebRTCCallbacks {
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Error) => void;
  onRemoteAudio?: (stream: MediaStream) => void;
}

export class WebRTCClient {
  private ws: WebSocket | null = null;
  private pc: RTCPeerConnection | null = null;
  private localStream: MediaStream | null = null;
  private callbacks: WebRTCCallbacks;
  private sessionId: string;

  private static ICE_SERVERS = [
    { urls: "stun:stun.l.google.com:19302" },
    { urls: "stun:stun1.l.google.com:19302" },
  ];

  constructor(callbacks: WebRTCCallbacks) {
    this.callbacks = callbacks;
    this.sessionId = crypto.randomUUID();
  }

  async connect(): Promise<void> {
    // Connect signaling channel
    await this.connectSignaling();

    // Get local audio
    this.localStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: CONFIG.AUDIO.SAMPLE_RATE,
      },
      video: false,
    });

    // Create peer connection
    this.pc = new RTCPeerConnection({ iceServers: WebRTCClient.ICE_SERVERS });

    // Add local tracks
    for (const track of this.localStream.getTracks()) {
      this.pc.addTrack(track, this.localStream);
    }

    // Handle remote stream (TTS audio from server)
    this.pc.ontrack = (event) => {
      this.callbacks.onRemoteAudio?.(event.streams[0]);
    };

    // ICE candidate handling
    this.pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.signal({ type: "ice_candidate", candidate: event.candidate });
      }
    };

    this.pc.onconnectionstatechange = () => {
      if (this.pc?.connectionState === "connected") {
        this.callbacks.onConnected?.();
      } else if (
        this.pc?.connectionState === "disconnected" ||
        this.pc?.connectionState === "failed"
      ) {
        this.callbacks.onDisconnected?.();
      }
    };

    // Create and send offer
    const offer = await this.pc.createOffer({ offerToReceiveAudio: true });
    await this.pc.setLocalDescription(offer);

    this.signal({ type: "offer", sdp: offer });
  }

  private connectSignaling(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`${CONFIG.WEBRTC_URL}/${this.sessionId}`);

      this.ws.onopen = () => resolve();
      this.ws.onerror = () => reject(new Error("Signaling connection failed"));

      this.ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "answer" && this.pc) {
          await this.pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
        } else if (msg.type === "ice_candidate" && this.pc && msg.candidate) {
          await this.pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
        }
      };
    });
  }

  private signal(data: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ session_id: this.sessionId, ...data }));
    }
  }

  disconnect(): void {
    this.localStream?.getTracks().forEach((t) => t.stop());
    this.pc?.close();
    this.ws?.close();
    this.pc = null;
    this.ws = null;
    this.localStream = null;
  }
}
