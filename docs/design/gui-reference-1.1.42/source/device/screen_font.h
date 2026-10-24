#pragma once
#include "esp_err.h"
#include "lvgl.h"
/* Display-task owned, single software draw unit. Fonts and borrowed glyph
 * bitmaps live until delete; delete only after associated labels are gone. */
typedef struct screen_font *screen_font_handle_t;
typedef struct { unsigned cache_slots; } screen_font_config_t;
esp_err_t screen_font_create(const screen_font_config_t *config,screen_font_handle_t *out);
void screen_font_delete(screen_font_handle_t handle);
const lv_font_t *screen_font_get(screen_font_handle_t handle,unsigned size);
