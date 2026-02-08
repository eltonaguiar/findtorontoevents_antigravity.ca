/**
 * Player.js
 * First-person player controller
 */

export class Player {
    constructor(engine) {
        this.engine = engine;
        this.camera = engine.getCamera();

        // Player properties
        this.position = new THREE.Vector3(0, 1.7, 5);
        this.velocity = new THREE.Vector3();
        this.rotation = new THREE.Euler(0, 0, 0, 'YXZ');

        // Movement settings
        this.moveSpeed = 5.0;
        this.sprintSpeed = 8.0;
        this.crouchSpeed = 2.5;
        this.jumpForce = 6.0;
        this.gravity = -20.0;

        // State
        this.isGrounded = true;
        this.isSprinting = false;
        this.isCrouching = false;

        // Input
        this.keys = {};
        this.mouse = { x: 0, y: 0 };
        this.mouseSensitivity = 0.002;

        this.init();
    }

    init() {
        // Set initial camera position
        this.camera.position.copy(this.position);
        this.camera.rotation.copy(this.rotation);

        // Setup input listeners
        this.setupInput();

        console.log('[Player] Initialized');
    }

    setupInput() {
        // Keyboard
        document.addEventListener('keydown', (e) => {
            this.keys[e.code] = true;

            // Sprint
            if (e.code === 'ShiftLeft') this.isSprinting = true;

            // Crouch
            if (e.code === 'ControlLeft') this.isCrouching = true;

            // Jump
            if (e.code === 'Space' && this.isGrounded) {
                this.velocity.y = this.jumpForce;
                this.isGrounded = false;
            }
        });

        document.addEventListener('keyup', (e) => {
            this.keys[e.code] = false;

            if (e.code === 'ShiftLeft') this.isSprinting = false;
            if (e.code === 'ControlLeft') this.isCrouching = false;
        });

        // Mouse movement
        document.addEventListener('mousemove', (e) => {
            if (document.pointerLockElement === this.engine.canvas) {
                this.mouse.x += e.movementX * this.mouseSensitivity;
                this.mouse.y += e.movementY * this.mouseSensitivity;

                // Clamp vertical rotation
                this.mouse.y = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, this.mouse.y));

                // Update camera rotation
                this.rotation.set(this.mouse.y, this.mouse.x, 0);
                this.camera.rotation.copy(this.rotation);
            }
        });
    }

    update(deltaTime) {
        // Calculate movement direction
        const moveDirection = new THREE.Vector3();

        if (this.keys['KeyW']) moveDirection.z -= 1;
        if (this.keys['KeyS']) moveDirection.z += 1;
        if (this.keys['KeyA']) moveDirection.x -= 1;
        if (this.keys['KeyD']) moveDirection.x += 1;

        // Normalize and apply speed
        if (moveDirection.length() > 0) {
            moveDirection.normalize();

            // Determine speed based on state
            let speed = this.moveSpeed;
            if (this.isSprinting) speed = this.sprintSpeed;
            if (this.isCrouching) speed = this.crouchSpeed;

            // Apply camera rotation to movement
            moveDirection.applyEuler(new THREE.Euler(0, this.rotation.y, 0));

            // Update velocity
            this.velocity.x = moveDirection.x * speed;
            this.velocity.z = moveDirection.z * speed;
        } else {
            // Decelerate
            this.velocity.x *= 0.9;
            this.velocity.z *= 0.9;
        }

        // Apply gravity
        if (!this.isGrounded) {
            this.velocity.y += this.gravity * deltaTime;
        }

        // Update position
        this.position.x += this.velocity.x * deltaTime;
        this.position.y += this.velocity.y * deltaTime;
        this.position.z += this.velocity.z * deltaTime;

        // Simple ground check (placeholder)
        if (this.position.y <= 1.7) {
            this.position.y = 1.7;
            this.velocity.y = 0;
            this.isGrounded = true;
        }

        // Update camera position
        this.camera.position.copy(this.position);
    }
}
