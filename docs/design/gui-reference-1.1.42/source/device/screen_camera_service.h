#pragma once
#include "screen_io.h"
typedef enum {SCREEN_CAMERA_IDLE,SCREEN_CAMERA_STARTING,SCREEN_CAMERA_RUNNING,SCREEN_CAMERA_STOPPING,SCREEN_CAMERA_ERROR} screen_camera_phase_t;
/* Page and explicit raw clients have independent capture intents. Raw false is
 * a global stop; a subsequent page entry or explicit enable can start again. */
esp_err_t screen_camera_service_page(screen_io_handle_t io,bool enabled);
esp_err_t screen_camera_service_raw(screen_io_handle_t io,bool enabled);
const char *screen_camera_phase_name(screen_camera_phase_t phase);
bool screen_camera_service_live(screen_io_handle_t io);
