// Type declarations for FPS V5 game globals

declare global {
    const THREE: any;

    interface Engine {
        scene: any;
        camera: any;
        renderer: any;
        isRunning: boolean;
    }

    interface Player {
        position: {
            x: number;
            y: number;
            z: number;
        };
    }

    const engine: Engine;
    const player: Player;
    const initGame: () => void;
}

export { };
