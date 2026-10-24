# Releasing a model for the app

The Zairenkai app downloads its model from a GitHub release of this repository, and only when
the user taps "Download model". It keeps the file only if its size and SHA-256 match the
`ModelManifest` packaged in the app.

| | |
|---|---|
| Release tag | `model-<model_id>` (for the current manifest: `model-qwen2_5_0_5b_instruct_q4_0`) |
| Model asset | the manifest's file name, unchanged (`qwen2.5-0.5b-instruct-q4_0.gguf`) |
| Other assets | `<model_id>.LICENSE.txt` (the weights' licence at the pinned revision), `<model_id>.manifest.json`, `SHA256SUMS` |
| App URL | `https://github.com/ZairenkaiPrjctX/Zairenkai-Intelligence-Engine/releases/download/<tag>/<file>` |

`tools/model_release.py urls <manifest>` prints these values. The app derives the same URL
from the manifest (`model_id` and file name), so the manifest needs no extra field and the SDK
schema stays as it is.

## Steps (maintainer)

1. Run the **Model release** workflow on `dev` with **draft_release** checked. It:
   - downloads the file the manifest names from its source, pinned to its revision;
   - checks the file against the manifest;
   - creates a **draft** release `model-<model_id>`.

   It refuses to create the draft if a release with that tag already exists.
2. Review the draft, then **publish** it. Until it is published, the app reports that the model
   release is not available yet, and the user can still import the file by hand. Agents never
   publish (`CLAUDE.md`).

A new or changed model needs a new manifest with a new `model_id`, and the app has to package
that manifest. A published release is never replaced.

## Why a release, not the APK

Packaging the model in the APK would make the APK about 470 MB, and every app update would
download the model again. The updater downloads whole APKs and refuses anything over 300 MB.
Storage use would also double, because llama.cpp needs the model as a file and so it would be
copied out of the APK.

From a release, the model is downloaded once (429 MB). The download resumes after an
interruption, and app updates stay small.
