export const CONFIG = {
  // WebSocket server URL
  WS_URL: process.env.WS_URL || "ws://localhost:8000/ws/audio",

  // WebRTC signaling URL
  WEBRTC_URL: process.env.WEBRTC_URL || "ws://localhost:8000/ws/webrtc",

  // Audio settings
  AUDIO: {
    SAMPLE_RATE: 16000,
    CHANNELS: 1,
    CHUNK_SIZE: 4096,
    FORMAT: "pcm16",
    SILENCE_THRESHOLD: 0.01,
    SILENCE_DURATION_MS: 1200, // ms of silence before sending
    MAX_RECORDING_MS: 30000,
  },

  // Connection
  RECONNECT_DELAY_MS: 2000,
  MAX_RECONNECT_ATTEMPTS: 5,
};
