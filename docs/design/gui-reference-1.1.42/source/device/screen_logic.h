#pragma once
#include <stdbool.h>
#include <stdint.h>
#define SCREEN_SIZE 480
#define SCREEN_JPEG_MAX (256 * 1024)
typedef enum { PAGE_STATUS, PAGE_WIDGET, PAGE_HOME, PAGE_TEXT, PAGE_CAMERA, PAGE_SETTINGS, PAGE_WIFI, PAGE_PASSWORD, PAGE_METRICS, PAGE_SENSORS, PAGE_API, PAGE_MESSAGE_SETTINGS } screen_page_t;
#define SCREEN_TOP_GESTURE_ZONE 32
#define SCREEN_BOTTOM_GESTURE_ZONE 72
#define SCREEN_VERTICAL_GESTURE_DISTANCE 28
#define SCREEN_HORIZONTAL_GESTURE_DISTANCE 56
#define SCREEN_TOUCH_TIMEOUT_MS 300
typedef struct {
    bool down, consumed;
    int history_delta;
    int x, y, start_x, start_y;
    uint32_t last_sample_ms;
} screen_touch_state_t;
struct screen_touch_sample { bool down; int x, y; uint32_t seq; int64_t timestamp_us; };
/* Valid samples are controller events; empty ACK reads preserve contact.
 * Navigation fires while moving and is consumed until the real release. */
screen_page_t screen_touch_update(screen_touch_state_t *s, screen_page_t page,
    bool valid_sample, bool down, int x, int y, uint32_t now_ms);
screen_page_t screen_navigate(screen_page_t page, int x0, int y0, int x1, int y1);
bool screen_jpeg_dimensions(const uint8_t *p, unsigned n);

static inline bool screen_is_main(screen_page_t page) {
    return page==PAGE_STATUS || page==PAGE_WIDGET || page==PAGE_HOME || page==PAGE_TEXT || page==PAGE_CAMERA;
}
