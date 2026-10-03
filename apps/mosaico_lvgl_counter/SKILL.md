---
{
  "name": "mosaico_lvgl_counter",
  "description": "Run a short ESP-Mosaico touchscreen counter demo with tap, reset and exit buttons. Requires the lvgl and system Lua modules and an available display.",
  "metadata": {
    "cap_groups": ["cap_lua"]
  }
}
---

# Mosaico LVGL Counter

Run this demo only when the user requests the counter or a touchscreen check.
It uses the screen temporarily, defaults to 60 seconds and allows early exit.
Do not replace or stop another screen-owning job automatically.

Start with `lua_run_script_async`:

```json
{
  "path": "{CUR_SKILL_DIR}/scripts/main.lua",
  "name": "mosaico_lvgl_counter",
  "exclusive": "display",
  "replace": false,
  "timeout_ms": 75000,
  "args": { "duration_seconds": 60 }
}
```

Keep the returned job id. Inspect its status and logs with `lua_get_async_job`
or `lua_tail_async_job`. A queued job or a `ready` log is not evidence that the
user has verified the screen and touch input.

To stop this demo, call `lua_stop_async_job` with its specific job id. Do not
stop all jobs. Report the actual error if APIs are unavailable or the display
is already owned by another job.

The script accepts `duration_seconds` from 5 to 120. If it is changed, make
the outer job timeout longer than the requested duration to allow cleanup.

English labels work with built-in fonts. The script optionally loads the
firmware's default TTF at several sizes and falls back to built-in fonts.
No credentials, network requests, camera, audio or GPIO are used.
