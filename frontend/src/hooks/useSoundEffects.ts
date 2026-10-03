"use client";

import { useCallback, useRef } from "react";

// Shared AudioContext instance to avoid creating multiple contexts
let globalAudioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;

  if (!globalAudioCtx) {
    const AudioCtxClass =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AudioCtxClass) {
      globalAudioCtx = new AudioCtxClass();
    }
  }

  if (globalAudioCtx && globalAudioCtx.state === "suspended") {
    globalAudioCtx.resume().catch(() => {});
  }

  return globalAudioCtx;
}

export function useSoundEffects() {
  const lastHoverTime = useRef<number>(0);

  /**
   * 1. playHover:
   * Tok ve hafif bir kaset/kutu sürtünme ve hava kayması sesi.
   * Filtrelenmiş beyaz gürültü + pes frekans süpürmesi ile sentezlenir.
   */
  const playHover = useCallback(() => {
    const now = Date.now();
    // Debounce to prevent acoustic clutter when mouse rapidly traverses items
    if (now - lastHoverTime.current < 70) return;
    lastHoverTime.current = now;

    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const duration = 0.085;
      const bufferSize = Math.floor(ctx.sampleRate * duration);
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = buffer.getChannelData(0);

      // Generate soft pink/white noise texture
      let lastOut = 0.0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        // Simple 1-pole filter for pink-ish warm noise
        output[i] = (lastOut + 0.025 * white) / 1.025;
        lastOut = output[i];
      }

      const noiseNode = ctx.createBufferSource();
      noiseNode.buffer = buffer;

      // Lowpass filter sweeping downwards to simulate friction
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(550, ctx.currentTime);
      filter.frequency.exponentialRampToValueAtTime(140, ctx.currentTime + duration);

      // Gentle, non-intrusive volume envelope
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.001, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.045, ctx.currentTime + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);

      // Complement with a subtle sub-bass woosh tone
      const subOsc = ctx.createOscillator();
      subOsc.type = "sine";
      subOsc.frequency.setValueAtTime(140, ctx.currentTime);
      subOsc.frequency.exponentialRampToValueAtTime(70, ctx.currentTime + duration);

      const subGain = ctx.createGain();
      subGain.gain.setValueAtTime(0.03, ctx.currentTime);
      subGain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);

      noiseNode.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      subOsc.connect(subGain);
      subGain.connect(ctx.destination);

      noiseNode.start(ctx.currentTime);
      subOsc.start(ctx.currentTime);
      subOsc.stop(ctx.currentTime + duration);
    } catch {
      // Audio playback fails silently if browser blocks autoplay
    }
  }, []);

  /**
   * 2. playChime:
   * Bir yapım "Altın Kutu" (Favori) yapıldığında çıkan sihirli, ışıltılı çınlama.
   * Uyumlu sine/triangle akor arpejleri ve kristal harmonikler.
   */
  const playChime = useCallback(() => {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const startTime = ctx.currentTime;
      // Magical shimmering notes (E6, G#6, B6, E7)
      const frequencies = [1318.51, 1661.22, 1975.53, 2637.02];

      frequencies.forEach((freq, index) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = index % 2 === 0 ? "sine" : "triangle";
        const noteStart = startTime + index * 0.045;
        const noteDuration = 0.42;

        osc.frequency.setValueAtTime(freq, noteStart);

        // Soft bell envelope with sparkling decay
        gain.gain.setValueAtTime(0.0001, noteStart);
        gain.gain.linearRampToValueAtTime(0.08, noteStart + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.0001, noteStart + noteDuration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(noteStart);
        osc.stop(noteStart + noteDuration + 0.05);
      });
    } catch {
      // Audio fails gracefully
    }
  }, []);

  /**
   * 3. playThud:
   * Bir yapım "Dropped" (Bırakıldı / Reddedildi) olarak işaretlendiğinde çıkan tok, pes çarpma sesi.
   */
  const playThud = useCallback(() => {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const startTime = ctx.currentTime;
      const duration = 0.16;

      // Heavy, bassy drop oscillator
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "triangle";
      osc.frequency.setValueAtTime(140, startTime);
      osc.frequency.exponentialRampToValueAtTime(36, startTime + duration);

      gain.gain.setValueAtTime(0.12, startTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);

      // Low click transient for physical impact tactile feel
      const click = ctx.createOscillator();
      const clickGain = ctx.createGain();
      click.type = "sine";
      click.frequency.setValueAtTime(260, startTime);
      click.frequency.exponentialRampToValueAtTime(60, startTime + 0.03);

      clickGain.gain.setValueAtTime(0.09, startTime);
      clickGain.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.03);

      osc.connect(gain);
      gain.connect(ctx.destination);

      click.connect(clickGain);
      clickGain.connect(ctx.destination);

      osc.start(startTime);
      click.start(startTime);

      osc.stop(startTime + duration + 0.02);
      click.stop(startTime + 0.04);
    } catch {
      // Audio fails gracefully
    }
  }, []);

  return {
    playHover,
    playChime,
    playThud,
  };
}
