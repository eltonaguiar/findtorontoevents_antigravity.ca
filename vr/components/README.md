# VR Chat Components

A-Frame components for VR chat interface with Quest 3 optimizations.

## Components

### vr-chat-panel.js
3D curved chat panel for VR environments.

**Features:**
- Curved panel attached to non-dominant hand or world space
- 3D message bubbles with user avatars
- Virtual keyboard integration
- Grab to reposition
- Pinch to scroll
- Double-tap to toggle mute

**Usage:**
```html
<!-- Attach to left hand -->
<a-entity vr-chat-panel="hand: left; radius: 1.5"></a-entity>

<!-- World space positioning -->
<a-entity vr-chat-panel="hand: world; worldPosition: 0 1.6 -2"></a-entity>

<!-- Full system -->
<a-entity vr-chat-system="enabled: true; hand: left"></a-entity>
```

**Schema Properties:**
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| hand | string | 'left' | 'left', 'right', or 'world' |
| radius | number | 1.5 | Curvature radius |
| width | number | 1.2 | Panel width |
| height | number | 0.8 | Panel height |
| maxMessages | number | 20 | Max visible messages |
| followHand | boolean | true | Follow hand movement |

---

### vr-voice-indicator.js
Spatial voice activity indicators above user avatars.

**Features:**
- Visual indicators for speaking/muted/idle states
- VU meter for audio levels
- Color coding (green=speaking, red=muted, gray=idle)
- Proximity-based visibility (fade beyond 10m)
- LOD system for performance

**Usage:**
```html
<!-- Single indicator -->
<a-entity vr-voice-indicator="userId: user123; height: 2.2"></a-entity>

<!-- Full voice manager for all users -->
<a-entity vr-voice-manager="enabled: true; indicatorHeight: 2.2"></a-entity>
```

**Schema Properties:**
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| userId | string | '' | User identifier |
| height | number | 2.2 | Height above avatar |
| size | number | 0.15 | Indicator size |
| fadeDistance | number | 10 | Fade start distance |
| cullDistance | number | 15 | Hide beyond distance |

---

### virtual-keyboard.js
VR text input keyboard with raycaster interaction.

**Features:**
- QWERTY, numeric, and emoji layouts
- Shift for uppercase
- Predictive text suggestions
- Laser pointer selection
- Haptic feedback on key press

**Usage:**
```html
<!-- Keyboard entity -->
<a-entity virtual-keyboard="onSubmit: handleSubmit; onClose: handleClose"></a-entity>

<!-- Full system -->
<a-entity vr-keyboard-system="enabled: true"></a-entity>
```

**Schema Properties:**
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| onSubmit | string | '' | Submit callback function name |
| onClose | string | '' | Close callback function name |
| initialText | string | '' | Starting text |
| maxLength | number | 200 | Max character limit |
| hapticFeedback | boolean | true | Enable haptic feedback |

---

### vr-chat-integration.js
Integration layer connecting components with vr-controls.js.

**Controller Bindings:**
| Action | Input | Description |
|--------|-------|-------------|
| Push-to-talk | Left grip + A | Hold to speak |
| Toggle mute | Right B (double-tap) | Mute/unmute mic |
| Toggle chat | Thumbstick press | Show/hide chat panel |
| Laser pointer | Trigger | Click keyboard keys |
| Grab panel | Grip | Move chat panel |

**Usage:**
```html
<script src="/vr/components/vr-chat-integration.js"></script>
<script>
  VRChatIntegration.init();
</script>
```

---

## Quest 3 Optimizations

All components implement these performance optimizations:

- **Low poly geometry**: 8-16 segment cylinders, simple boxes
- **Simple materials**: MeshBasicMaterial, no complex shaders
- **Object pooling**: Reuse message bubble entities
- **LOD system**: Simplified rendering at distance
- **Distance culling**: Hide elements beyond 15m
- **Throttled updates**: 30fps cap for non-critical updates
- **Batched rendering**: Minimize draw calls

---

## Demo

Open `vr/chat/vr-chat-demo.html` to test components in browser.

Keyboard shortcuts for testing:
- `M` - Toggle mute
- `C` - Toggle chat panel
- `T` - Send test message

---

## Integration with Existing Systems

### ChatEngine
Components automatically connect to global `ChatEngine` for:
- Message sending/receiving
- User presence updates
- Room management

### VoiceEngine
Components automatically connect to global `VoiceEngine` for:
- Mute state synchronization
- Voice activity detection
- Spatial audio positioning

### vr-controls.js
Integration layer provides:
- Controller event mapping
- Haptic feedback
- Laser pointer interaction
