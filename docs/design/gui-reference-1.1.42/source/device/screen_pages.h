#pragma once
#include "screen_app.h"
#include "screen_logic.h"
#include "screen_transition.h"
/* Locked producer calls: caller holds app lock. Last request replaces older
 * intent; explicit view wins over arrival. No queue grows with frame rate. */
void screen_pages_request_locked(screen_app_handle_t app,screen_page_t page);
void screen_pages_arrival_locked(screen_app_handle_t app,screen_page_t page,uint32_t id);
void screen_pages_cancel_arrival_locked(screen_app_handle_t app);
/* Display-task-only: consumes intents, coordinates lifecycle, publishes state.
 * Commit requires LCD DMA drained; UI construction is performed afterwards. */
void screen_pages_navigate(screen_app_handle_t app,screen_page_t page,screen_slide_t direction);
void screen_pages_resolve(screen_app_handle_t app,bool allow_push);
void screen_pages_commit(screen_app_handle_t app);
void screen_pages_presented(screen_app_handle_t app);
