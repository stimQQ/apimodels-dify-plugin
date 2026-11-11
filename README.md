# apimodels.app Image & Video

**Author:** apimodels
**Version:** 0.1.0
**Type:** tool
**Source:** https://github.com/stimQQ/apimodels-dify-plugin
**Contact:** support@apimodels.app

Generate and edit images and videos in Dify workflows, chatflows and agents with the image and video models on [apimodels.app](https://apimodels.app/?utm_source=dify&utm_medium=referral): GPT Image 2 / 2.5 / 2.6, Seedream 4.5 / 5.0 / 5.5, Nano Banana, Gemini image models, Qwen Image, Kling, MiniMax H3 Image, Seedance 2.0 / 2.5, Kling 4.0, Wan 3.0, MiniMax H3, Veo 3.1, Vidu Q4, LTX-2.3 and others. One API key covers all of them.

## Tools

| Tool | What it does |
|---|---|
| **Generate Image** | Text-to-image, or edit / combine reference images. Returns the image files and their links. |
| **Generate Video** | Text-to-video, first frame (and last frame) to video, or reference images to video. Returns the video file and its link. |
| **Get Task** | Checks a task by ID and returns the result once it is ready. |

Generation on apimodels.app is asynchronous. The tools submit the job and wait for it: up to 5 minutes for images and 9 minutes for videos. If a job is still running after that, the tool returns its task ID, and **Get Task** picks up the result later. Every task also appears in the [apimodels.app console](https://apimodels.app/console/records?utm_source=dify&utm_medium=referral).

The model dropdown is read live from the public model list (`GET https://api.apimodels.app/v1/models`), so models added to apimodels.app show up without a plugin update.

## Setup

1. Create an account at [apimodels.app](https://apimodels.app/?utm_source=dify&utm_medium=referral) and add credit to the balance.
2. Create an API key at [apimodels.app/console/api-keys](https://apimodels.app/console/api-keys?utm_source=dify&utm_medium=referral).
3. In Dify, install this plugin, open **Tools → apimodels.app Image & Video → Authorize**, and paste the key. The key is checked with a balance lookup, which costs nothing.

## Usage

### In a workflow

Add **Generate Image** or **Generate Video** as a node. Fill in the prompt and pick a model. Reference images and first / last frames can come from a Start node file input or from an earlier node. The node outputs:

- `files`: the generated images or video,
- `json`: `task_id`, `status`, `urls` and `credits` (the amount charged in USD),
- `text`: the result links.

### In an agent

Enable the tools in the agent. The agent fills in the prompt and the model ID; it defaults to `gpt-image-2.6-flare` for images and `seedance-2.0-fast` for videos unless the user asks for another model.

### Model-specific options

Common options (aspect ratio, resolution, quality, length, first / last frame, reference images) are separate fields. Anything else a model supports, such as a seed, an output format, audio on / off or Wan's `mode`, goes into **Extra parameters** as JSON, for example:

```json
{"seed": 42, "generate_audio": false}
```

Each model's fields are listed on its page in the [apimodels.app docs](https://apimodels.app/docs?utm_source=dify&utm_medium=referral). Video resolution is passed through as written, because models name their tiers differently (`720p`, `768p`, `1080P`, `2k`).

## Pricing

Usage is billed per generated image or per second of video to your apimodels.app balance, at the prices listed on [apimodels.app/pricing](https://apimodels.app/pricing?utm_source=dify&utm_medium=referral). Failed or rejected generations are not charged. The plugin itself is free.

## Limits and notes

- Result links are kept for 30 days. The files attached to the Dify message are copies; save the ones you need.
- Only result files on apimodels.app storage (`r2.apimodels.app`) are attached, up to 50 MB each; anything else is returned as a link and not fetched by the plugin.
- Input files (reference images, first / last frames) are uploaded to apimodels.app storage so the models can read them.
- Content moderation by the model providers can refuse some prompts or images. Refused jobs are not charged.
- Not every model accepts every input. If a combination is not supported, the API answers with an error that names the problem.

## Connection requirements

The Dify instance must be able to reach `https://api.apimodels.app` over HTTPS (outbound only), and download results from `https://r2.apimodels.app`.

## Privacy

See [PRIVACY.md](PRIVACY.md).

## Support

Open an issue at https://github.com/stimQQ/apimodels-dify-plugin/issues or write to support@apimodels.app.
