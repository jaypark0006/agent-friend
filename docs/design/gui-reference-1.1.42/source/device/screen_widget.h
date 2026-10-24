#pragma once
#include "screen_logic.h"
#include "esp_http_server.h"
#include "cJSON.h"
#include "lvgl.h"

#define SCREEN_WIDGET_MAX_QUEUE 16
#define SCREEN_WIDGET_ID_MAX 64
#define SCREEN_WIDGET_TITLE_MAX 64
#define SCREEN_WIDGET_STATUS_MAX 128
#define SCREEN_WIDGET_BADGE_MAX 32

struct screen_agent_item {
    bool active;
    bool done;
    char id[SCREEN_WIDGET_ID_MAX+1];
    char title[SCREEN_WIDGET_TITLE_MAX+1];
    char status[SCREEN_WIDGET_STATUS_MAX+1];
    char badge[SCREEN_WIDGET_BADGE_MAX+1];
    int progress; /* 0..100, or -1 if hidden */
    uint32_t color_hex;
    int64_t created_us;
    int64_t update_us;
    char action_type[16];   /* "confirm", or "" */
    char action_btn1[24];   /* e.g. "Approve" */
    char action_btn2[24];   /* e.g. "Cancel" */
    char action_result[24]; /* "Approve", "Cancel", or "" */
};

struct screen_widget_state {
    struct screen_agent_item items[SCREEN_WIDGET_MAX_QUEUE];
    uint32_t count;
    uint32_t active_count;
    uint32_t done_count;
    uint32_t generation;
    int64_t update_us;
};

struct screen_app;
void screen_widget_init(struct screen_app *a);
esp_err_t screen_widget_update(struct screen_app *a, const cJSON *json, bool *switch_to_widget);
cJSON *screen_widget_json(struct screen_app *a);
esp_err_t screen_http_widget(httpd_req_t *r);
void screen_ui_widget_build(struct screen_app *a, lv_obj_t *root);
void screen_ui_widget_refresh(struct screen_app *a);
bool screen_widget_trigger_action(struct screen_app *a, int which);
