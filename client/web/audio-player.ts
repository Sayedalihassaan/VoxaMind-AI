export interface AudioPlayerOptions {
  onPlaybackStart?: () => void;
  onPlaybackEnd?: () => void;
  onError?: (error: Error) => void;
}

export class AudioPlayer {
  private audioContext: AudioContext;
  private queue: AudioBuffer[] = [];
  private isPlaying = false;
  private currentSource: AudioBufferSourceNode | null = null;
  private options: AudioPlayerOptions;
  private gainNode: GainNode;

  constructor(options: AudioPlayerOptions = {}) {
    this.options = options;
    this.audioContext = new AudioContext();
    this.gainNode = this.audioContext.createGain();
    this.gainNode.connect(this.audioContext.destination);
  }

  /**
   * Queue raw PCM audio bytes (Int16, mono, 22050 Hz by default)
   */
  async queueAudio(data: ArrayBuffer, sampleRate = 22050): Promise<void> {
    const int16 = new Int16Array(data);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768.0;
    }

    const audioBuffer = this.audioContext.createBuffer(1, float32.length, sampleRate);
    audioBuffer.copyToChannel(float32, 0);

    this.queue.push(audioBuffer);

    if (!this.isPlaying) {
      this.playNext();
    }
  }

  /**
   * Queue audio from a Blob (mp3, wav, ogg)
   */
  async queueBlob(blob: Blob): Promise<void> {
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
    this.queue.push(audioBuffer);

    if (!this.isPlaying) {
      this.playNext();
    }
  }

  private playNext(): void {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      this.options.onPlaybackEnd?.();
      return;
    }

    this.isPlaying = true;
    const buffer = this.queue.shift()!;

    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.gainNode);
    this.currentSource = source;

    source.onended = () => {
      this.currentSource = null;
      this.playNext();
    };

    if (this.queue.length === 0 && this.options.onPlaybackStart) {
      this.options.onPlaybackStart();
    }

    source.start(0);
  }

  stop(): void {
    this.queue = [];
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch (_) {}
      this.currentSource = null;
    }
    this.isPlaying = false;
  }

  setVolume(volume: number): void {
    this.gainNode.gain.value = Math.max(0, Math.min(1, volume));
  }

  get playing(): boolean {
    return this.isPlaying;
  }

  get queueLength(): number {
    return this.queue.length;
  }

  async resume(): Promise<void> {
    if (this.audioContext.state === "suspended") {
      await this.audioContext.resume();
    }
  }

  destroy(): void {
    this.stop();
    this.audioContext.close();
  }
}
