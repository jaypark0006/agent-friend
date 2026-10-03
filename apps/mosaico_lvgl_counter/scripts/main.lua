-- ESP-Mosaico Lua/LVGL touch demo. Default: stop after 60 seconds.
-- API reference: ESP-Claw 9f92961687df06250df62c187979fa1ff67708f4.
-- Device compatibility and screen rendering still require a real-device run.
local lvgl = require("lvgl")
local system = require("system")

for _, name in ipairs({ "init", "create_screen", "label", "button",
                        "process_events", "deinit" }) do
    assert(type(lvgl[name]) == "function", "Missing lvgl API: " .. name)
end
assert(type(system.millis) == "function", "Missing system.millis API")

local options = type(args) == "table" and args or {}
local duration = tonumber(options.duration_seconds) or 60
assert(duration >= 5 and duration <= 120,
       "duration_seconds must be between 5 and 120")
duration = math.floor(duration)

local initialized = false
local running = true
local count = 0
local reason = "time_limit"

local function optional_font(size)
    if type(lvgl.font_load) ~= "function" then return nil end
    local ok, font = pcall(lvgl.font_load, { size = size, cache_size = 64 })
    if ok then return font end
    print("[mosaico_lvgl_counter] using built-in font for size=" .. size)
    return nil
end

local function run()
    lvgl.init({ buffer_lines = 40, tick_ms = 5, task_period_ms = 10 })
    initialized = true

    local font_small = optional_font(18)
    local font_button = optional_font(24)
    local font_count = optional_font(72)
    local screen = lvgl.create_screen()
    screen:set_style({ bg_color = "#11141a", pad = 0, border_width = 0 })

    lvgl.label(screen, {
        text = "MOSAICO / LVGL", align = "top_mid", y = 36,
        text_color = "#f4f6fa", font = font_button,
    })
    lvgl.label(screen, {
        text = "Tap. Reset. Exit.", align = "top_mid", y = 80,
        text_color = "#919bab", font = font_small,
    })
    lvgl.label(screen, {
        text = "TAPS", align = "center", y = -96,
        text_color = "#919bab", font = font_small,
    })
    local counter = lvgl.label(screen, {
        text = "0", align = "center", y = -36,
        text_color = "#ffffff", font = font_count,
    })
    local add = lvgl.button(screen, {
        text = "+1 TAP", align = "center", y = 72, w = 384, h = 72,
        bg_color = "#ff914d", text_color = "#17191e",
        radius = 20, border_width = 0, font = font_button,
    })
    local reset = lvgl.button(screen, {
        text = "Reset", align = "bottom_left", x = 48, y = -58,
        w = 184, h = 56, bg_color = "#242c38", text_color = "#f4f6fa",
        radius = 16, border_width = 0, font = font_button,
    })
    local exit = lvgl.button(screen, {
        text = "Exit", align = "bottom_right", x = -48, y = -58,
        w = 184, h = 56, bg_color = "#242c38", text_color = "#f4f6fa",
        radius = 16, border_width = 0, font = font_button,
    })
    local footer = lvgl.label(screen, {
        text = "Auto-exit in " .. duration .. "s",
        align = "bottom_mid", y = -24,
        text_color = "#919bab", font = font_small,
    })

    add:on("clicked", function()
        count = count + 1
        counter:set_text(tostring(count))
        counter:align("center", 0, -36)
        print("[mosaico_lvgl_counter] count=" .. count)
    end)
    reset:on("clicked", function()
        count = 0
        counter:set_text("0")
        counter:align("center", 0, -36)
        print("[mosaico_lvgl_counter] reset")
    end)
    exit:on("clicked", function()
        reason = "exit_button"
        running = false
    end)

    screen:load()
    print("[mosaico_lvgl_counter] ready duration_seconds=" .. duration)
    local deadline = system.millis() + duration * 1000
    local previous_remaining = duration
    while running do
        local remaining = math.ceil((deadline - system.millis()) / 1000)
        if remaining <= 0 then break end
        if remaining ~= previous_remaining then
            footer:set_text("Auto-exit in " .. remaining .. "s")
            previous_remaining = remaining
        end
        lvgl.process_events(50)
    end
end

local ok, failure = xpcall(run, function(err) return tostring(err) end)
if initialized then
    local cleanup_ok, cleanup_error = pcall(lvgl.deinit)
    if not cleanup_ok then
        print("[mosaico_lvgl_counter] cleanup failed: " .. tostring(cleanup_error))
        if ok then ok, failure = false, cleanup_error end
    end
end
if not ok then error(failure, 0) end
print("[mosaico_lvgl_counter] done reason=" .. reason .. " count=" .. count)
