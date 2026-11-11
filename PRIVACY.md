# Privacy Policy

This plugin connects Dify to the apimodels.app API (`https://api.apimodels.app`). It does not collect, store or log any data itself.

## What is sent, and where

When a tool runs, the plugin sends the following to apimodels.app over HTTPS:

- your apimodels.app API key, to authenticate the request;
- the prompt and the options you set (model, aspect ratio, resolution, length, extra parameters);
- any input files (reference images, first / last frames). Files are uploaded to apimodels.app storage so the model can read them; links you provide are passed on as they are.

apimodels.app forwards the request to the provider of the model you picked (for example OpenAI, Google, ByteDance, Kuaishou, Alibaba or MiniMax) to generate the result. Generated files are stored by apimodels.app and are reachable by link for 30 days.

The plugin also reads the public model list (`GET https://api.apimodels.app/v1/models`) to fill the model dropdown. That request carries no key and no user data.

## What the plugin keeps

Nothing. The API key is stored by Dify as an encrypted credential. The plugin keeps no copies of prompts, files or results, and writes no logs of them.

## apimodels.app

How apimodels.app handles requests, files and account data is described in its privacy policy: https://apimodels.app/privacy

## Contact

support@apimodels.app
