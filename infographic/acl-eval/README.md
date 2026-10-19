# ACL Infographic Generation

This directory contains the prepared content for generating an infographic about ServiceNow ACL evaluation flow.

## Files

- `source.md` – raw content
- `analysis.md` – analysis of topic, audience, etc.
- `structured-content.md` – structured content for infographic
- `prompts/infographic.md` – final prompt for image generation

## How to Generate the Infographic

1. Ensure you have an image generation API key configured (e.g., FAL_KEY for Fal.ai).
2. Run the `baoyu-infographic` skill with the prompt file:
   ```
   # Assuming you are in the Hermes agent environment
   # Use the skill to generate image from the prompt
   ```
   Alternatively, you can manually use an image generation service with the prompt in `prompts/infographic.md`.

3. The generated image will be saved as `infographic.png` in this directory.

## Note

Image generation requires the `FAL_KEY` environment variable to be set. Without it, the `image_generate` tool will fail.
