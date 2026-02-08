/**
 * GameEngine.js
 * Core Three.js rendering engine for FPS V5
 */

export class GameEngine {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.clock = new THREE.Clock();
        this.deltaTime = 0;
        this.fps = 60;
        this.frameCount = 0;
        this.lastFpsUpdate = 0;
        this.isRunning = false;
    }

    async init() {
        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x87ceeb); // Sky blue
        this.scene.fog = new THREE.Fog(0x87ceeb, 50, 200);

        // Create camera
        this.camera = new THREE.PerspectiveCamera(
            75, // FOV
            window.innerWidth / window.innerHeight, // Aspect ratio
            0.1, // Near plane
            1000 // Far plane
        );
        this.camera.position.set(0, 1.7, 5); // Eye height ~1.7m

        // Create renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());

        console.log('[Engine] Initialized successfully');
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    start() {
        this.isRunning = true;
        this.animate();
        console.log('[Engine] Started game loop');
    }

    stop() {
        this.isRunning = false;
        console.log('[Engine] Stopped game loop');
    }

    animate() {
        if (!this.isRunning) return;

        requestAnimationFrame(() => this.animate());

        // Calculate delta time
        this.deltaTime = this.clock.getDelta();

        // Update FPS counter
        this.frameCount++;
        const currentTime = performance.now();
        if (currentTime - this.lastFpsUpdate >= 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastFpsUpdate = currentTime;

            // Update FPS display
            const fpsElement = document.getElementById('fps-value');
            if (fpsElement) {
                fpsElement.textContent = this.fps;
                fpsElement.style.color = this.fps >= 55 ? '#22c55e' : this.fps >= 30 ? '#f59e0b' : '#ef4444';
            }
        }

        // Render scene
        this.renderer.render(this.scene, this.camera);
    }

    // Utility methods
    getCamera() {
        return this.camera;
    }

    getScene() {
        return this.scene;
    }

    getDeltaTime() {
        return this.deltaTime;
    }

    getFPS() {
        return this.fps;
    }
}
