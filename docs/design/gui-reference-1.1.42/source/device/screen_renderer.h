#pragma once
#include "screen_app.h"
#include <stdbool.h>
#include <stdint.h>
typedef struct {
    bool camera,counts_frame;
    uint32_t history_id,selected_id;
    int64_t received_us;
} screen_rendered_frame_t;
/* Display task owns the spare output buffer. JPEG slots are borrowed only
 * through decode; camera slots only through conversion. No LCD submission. */
bool screen_renderer_prepare(screen_app_handle_t app,screen_rendered_frame_t *frame);
void screen_renderer_badge(screen_app_handle_t app,uint8_t *pixels);
