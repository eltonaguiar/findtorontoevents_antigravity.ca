/**
 * notificationSounds.ts
 * 
 * Web Audio API-based notification sound system for FavCreators.
 * Synthesizes pleasant notification sounds without external audio files.
 * 
 * Two built-in sounds:
 *   - "ding"  — simple single-tone ding for non-bell creators going live
 *   - "bell"  — richer two-tone chime for bell-icon (priority) creators
 * 
 * Supports custom sounds via URL for logged-in users.
 */

// ── localStorage keys ──
const KEYS = {
  soundEnabled: 'fc_notif_sound_enabled',
  volume: 'fc_notif_sound_volume',
  bellSound: 'fc_notif_sound_bell',     // "default" | custom URL
  normalSound: 'fc_notif_sound_normal', // "default" | custom URL
  browserNotifEnabled: 'fc_notif_browser_enabled',
} as const;

// ── Preferences helpers ──

export function isSoundEnabled(): boolean {
  const v = localStorage.getItem(KEYS.soundEnabled);
  return v === null ? true : v === 'true';
}

export function setSoundEnabled(enabled: boolean): void {
  localStorage.setItem(KEYS.soundEnabled, String(enabled));
}

export function getVolume(): number {
  const v = localStorage.getItem(KEYS.volume);
  if (v === null) return 0.5;
  const n = parseFloat(v);
  return isNaN(n) ? 0.5 : Math.max(0, Math.min(1, n));
}

export function setVolume(vol: number): void {
  localStorage.setItem(KEYS.volume, String(Math.max(0, Math.min(1, vol))));
}

export function getBellSoundPref(): string {
  return localStorage.getItem(KEYS.bellSound) || 'default';
}

export function setBellSoundPref(val: string): void {
  localStorage.setItem(KEYS.bellSound, val);
}

export function getNormalSoundPref(): string {
  return localStorage.getItem(KEYS.normalSound) || 'default';
}

export function setNormalSoundPref(val: string): void {
  localStorage.setItem(KEYS.normalSound, val);
}

export function isBrowserNotifEnabled(): boolean {
  const v = localStorage.getItem(KEYS.browserNotifEnabled);
  return v === 'true';
}

export function setBrowserNotifEnabled(enabled: boolean): void {
  localStorage.setItem(KEYS.browserNotifEnabled, String(enabled));
}

// ── Audio Context singleton ──

let _ctx: AudioContext | null = null;

function getAudioContext(): AudioContext {
  if (!_ctx || _ctx.state === 'closed') {
    _ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  }
  // Resume if suspended (browsers require user gesture)
  if (_ctx.state === 'suspended') {
    _ctx.resume().catch(() => {});
  }
  return _ctx;
}

// ── Built-in synthesized sounds ──

/**
 * Play a simple pleasant ding — single sine tone with quick decay.
 * Used for non-bell (normal) creators going live.
 */
export function playDefaultDing(volumeOverride?: number): void {
  try {
    const ctx = getAudioContext();
    const vol = volumeOverride ?? getVolume();
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(830, now);           // E5-ish
    osc.frequency.exponentialRampToValueAtTime(620, now + 0.15); // descend slightly

    gain.gain.setValueAtTime(vol * 0.6, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.55);
  } catch (e) {
    console.warn('[NotifSound] Failed to play default ding:', e);
  }
}

/**
 * Play a richer two-tone bell chime — used for bell-icon (priority) creators.
 * Two harmonically related sine tones for a distinctive sound.
 */
export function playBellSound(volumeOverride?: number): void {
  try {
    const ctx = getAudioContext();
    const vol = volumeOverride ?? getVolume();
    const now = ctx.currentTime;

    // Tone 1 — higher pitch
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(1047, now);  // C6
    gain1.gain.setValueAtTime(vol * 0.5, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.65);

    // Tone 2 — slightly delayed, lower
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(1319, now + 0.12);  // E6
    gain2.gain.setValueAtTime(0, now);
    gain2.gain.setValueAtTime(vol * 0.45, now + 0.12);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.8);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start(now);
    osc2.stop(now + 0.85);

    // Subtle third harmonic for richness
    const osc3 = ctx.createOscillator();
    const gain3 = ctx.createGain();
    osc3.type = 'sine';
    osc3.frequency.setValueAtTime(1568, now + 0.06);  // G6
    gain3.gain.setValueAtTime(0, now);
    gain3.gain.setValueAtTime(vol * 0.2, now + 0.06);
    gain3.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
    osc3.connect(gain3);
    gain3.connect(ctx.destination);
    osc3.start(now);
    osc3.stop(now + 0.55);
  } catch (e) {
    console.warn('[NotifSound] Failed to play bell sound:', e);
  }
}

/**
 * Play a custom sound from a URL (data: URL or http URL).
 * Falls back to the appropriate built-in sound on error.
 */
export async function playCustomSound(url: string, fallback: 'ding' | 'bell' = 'ding'): Promise<void> {
  try {
    const audio = new Audio(url);
    audio.volume = getVolume();
    await audio.play();
  } catch (e) {
    console.warn('[NotifSound] Custom sound failed, using fallback:', e);
    if (fallback === 'bell') {
      playBellSound();
    } else {
      playDefaultDing();
    }
  }
}

// ── Main notification sound dispatcher ──

/**
 * Play the appropriate notification sound for a creator going live.
 * 
 * @param isBellCreator  true if this creator has the bell icon enabled (priority)
 */
export function playLiveNotificationSound(isBellCreator: boolean): void {
  if (!isSoundEnabled()) return;

  if (isBellCreator) {
    const pref = getBellSoundPref();
    if (pref && pref !== 'default') {
      playCustomSound(pref, 'bell');
    } else {
      playBellSound();
    }
  } else {
    const pref = getNormalSoundPref();
    if (pref && pref !== 'default') {
      playCustomSound(pref, 'ding');
    } else {
      playDefaultDing();
    }
  }
}

// ── Browser Notification helpers ──

export function getBrowserNotifPermission(): NotificationPermission | 'unsupported' {
  if (typeof Notification === 'undefined') return 'unsupported';
  return Notification.permission;
}

export async function requestBrowserNotifPermission(): Promise<NotificationPermission | 'unsupported'> {
  if (typeof Notification === 'undefined') return 'unsupported';
  const perm = await Notification.requestPermission();
  if (perm === 'granted') {
    setBrowserNotifEnabled(true);
  }
  return perm;
}

export function showBrowserNotification(
  title: string,
  body: string,
  options?: { icon?: string; tag?: string; url?: string }
): void {
  if (typeof Notification === 'undefined') return;
  if (Notification.permission !== 'granted') return;
  if (!isBrowserNotifEnabled()) return;

  try {
    const notif = new Notification(title, {
      body,
      icon: options?.icon || '/fc/favicon.ico',
      tag: options?.tag,
    });
    if (options?.url) {
      notif.onclick = () => {
        window.focus();
        notif.close();
      };
    }
    // Auto-close after 8 seconds
    setTimeout(() => notif.close(), 8000);
  } catch (e) {
    console.warn('[NotifSound] Browser notification failed:', e);
  }
}
