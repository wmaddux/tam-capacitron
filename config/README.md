# Input configuration

**`inputs.json`** is the single source for:

- **defaults** – default values for all capacity inputs (used by "Load from defaults", the API, and the engine).
- **sliders** – `min`, `max`, and `step` for each slider in the UI.

Edit `inputs.json` and restart the app to change defaults or slider ranges. The UI loads this via `GET /api/input-config`.
