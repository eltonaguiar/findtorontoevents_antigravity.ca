
import { grabAvatarV4 } from './src/utils/avatarGrabberV4.js';

const accounts = [
    { platform: 'tiktok', username: 'chavcriss' },
    { platform: 'instagram', username: 'chavcriss' },
    { platform: 'youtube', username: 'chavcriss' }
];

async function test() {
    console.log("Testing Chavcriss avatar fetch...");
    try {
        const result = await grabAvatarV4(accounts, "Chavcriss");
        console.log("Result:", JSON.stringify(result, null, 2));
    } catch (err) {
        console.error("Error:", err);
    }
}

test();
