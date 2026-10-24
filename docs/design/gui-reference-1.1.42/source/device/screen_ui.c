#ifdef SCREEN_SIM
#include "screen_sim_private.h"
#else
#include "screen_private.h"
#endif
#include "bsp/esp_mosaico.h"
#include "esp_system.h"
#include "esp_app_desc.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>

LV_FONT_DECLARE(screen_font_cjk_16);

struct status_card_schema {
    int16_t x, y, w, h;
    uint32_t bg_hex;
    uint32_t border_hex;
    uint32_t header_hex;
    const char *header_text;
};

struct status_dashboard_handles {
    lv_obj_t *dot;
    lv_obj_t *ip_label;
    lv_obj_t *wifi_label;
    lv_obj_t *power_label;
    lv_obj_t *sensor_label;
    lv_obj_t *engine_label;
};

static struct status_dashboard_handles s_status_ui = {0};

void screen_ui_refresh_battery(struct screen_app *a)
{
    if(!a || !a->header_battery) return;
    bool bat_ok = a->sensors.battery_ok;
    int soc = a->sensors.battery.state_of_charge;
    int i_ma = a->sensors.battery.current_ma;

    char buf[32];
    uint32_t color = 0xc5d1de;

    if(bat_ok) {
        if(soc > 100) soc = 100;
        if(soc < 0) soc = 0;
        if(i_ma > 15) {
            snprintf(buf, sizeof(buf), LV_SYMBOL_CHARGE " %d%%", soc);
            color = 0x39e69d;
        } else {
            const char *sym;
            if(soc >= 80) sym = LV_SYMBOL_BATTERY_FULL;
            else if(soc >= 55) sym = LV_SYMBOL_BATTERY_3;
            else if(soc >= 30) sym = LV_SYMBOL_BATTERY_2;
            else if(soc >= 12) sym = LV_SYMBOL_BATTERY_1;
            else sym = LV_SYMBOL_BATTERY_EMPTY;

            snprintf(buf, sizeof(buf), "%s %d%%", sym, soc);

            if(soc <= 10) color = 0xff5555;
            else if(soc <= 20) color = 0xe5c07b;
            else color = 0xc5d1de;
        }
    } else {
        snprintf(buf, sizeof(buf), LV_SYMBOL_CHARGE " USB");
        color = 0x4fa3e3;
    }

    lv_label_set_text(a->header_battery, buf);
    lv_obj_set_style_text_color(a->header_battery, lv_color_hex(color), 0);
}

static void page_dot_click_cb(lv_event_t *e)
{
    struct screen_app *a = lv_event_get_user_data(e);
    lv_obj_t *dot = lv_event_get_target_obj(e);
    uintptr_t target_idx = (uintptr_t)lv_obj_get_user_data(dot);
    const screen_page_t pages[] = {PAGE_STATUS, PAGE_WIDGET, PAGE_HOME, PAGE_TEXT, PAGE_CAMERA};
    if(target_idx < 5 && a) {
        screen_pages_navigate(a, pages[target_idx], SCREEN_SLIDE_NONE);
    }
}

void screen_ui_draw_page_dots(struct screen_app *a, lv_obj_t *parent, int active_idx, int total)
{
    lv_obj_t *box=lv_obj_create(parent);
    lv_obj_set_size(box,total*16,20);
    lv_obj_set_pos(box,460-total*16,20);
    lv_obj_set_style_bg_opa(box,LV_OPA_TRANSP,0);
    lv_obj_set_style_border_width(box,0,0);
    lv_obj_set_style_pad_all(box,0,0);
    lv_obj_remove_flag(box,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_flex_flow(box,LV_FLEX_FLOW_ROW);
    lv_obj_set_style_pad_column(box,6,0);
    lv_obj_set_flex_align(box,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);

    for(int i=0;i<total;i++) {
        lv_obj_t *dot=lv_obj_create(box);
        bool act=(i==active_idx);
        lv_obj_set_size(dot,act?9:6,act?9:6);
        lv_obj_set_style_radius(dot,LV_RADIUS_CIRCLE,0);
        lv_obj_set_style_bg_color(dot,lv_color_hex(act?0x39e69d:0x324254),0);
        lv_obj_set_style_border_width(dot,0,0);
        lv_obj_remove_flag(dot,LV_OBJ_FLAG_SCROLLABLE);
        if(a) {
            lv_obj_add_flag(dot,LV_OBJ_FLAG_CLICKABLE);
            lv_obj_set_ext_click_area(dot,8);
            lv_obj_set_user_data(dot,(void*)(uintptr_t)i);
            lv_obj_add_event_cb(dot,page_dot_click_cb,LV_EVENT_CLICKED,a);
        }
    }

    if(a) {
        a->header_battery = lv_label_create(parent);
        lv_obj_set_pos(a->header_battery, 460 - total*16 - 76, 20);
        lv_obj_set_size(a->header_battery, 72, 20);
        lv_obj_set_style_text_align(a->header_battery, LV_TEXT_ALIGN_RIGHT, 0);
        lv_obj_set_style_text_font(a->header_battery, &lv_font_montserrat_14, 0);
        screen_ui_refresh_battery(a);
    }
}

static lv_obj_t *label(lv_obj_t *parent,const char *text,int x,int y,int width)
{
    lv_obj_t *l=lv_label_create(parent); lv_label_set_text(l,text);
    lv_obj_set_pos(l,x,y); lv_obj_set_width(l,width); return l;
}

static lv_obj_t *button(struct screen_app *a,lv_obj_t *parent,const char *text,int x,int y,int w,int h,lv_event_cb_t cb)
{
    lv_obj_t *b=lv_button_create(parent); lv_obj_set_pos(b,x,y); lv_obj_set_size(b,w,h);
    lv_obj_set_style_bg_color(b,lv_color_hex(0x1c2b38),0);
    lv_obj_set_style_border_color(b,lv_color_hex(0x2c4056),0);
    lv_obj_set_style_border_width(b,1,0);
    lv_obj_set_style_radius(b,8,0);
    lv_obj_t *l=lv_label_create(b); lv_label_set_text(l,text); lv_obj_center(l);
    lv_obj_set_style_text_color(l,lv_color_hex(0xf0f4fa),0);
    lv_obj_add_event_cb(b,cb,LV_EVENT_CLICKED,a); return b;
}

static void home_click(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    screen_pages_navigate(a,a->main_page,SCREEN_SLIDE_NONE);
}

static void open_settings_click(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    screen_pages_navigate(a,PAGE_SETTINGS,SCREEN_SLIDE_NONE);
}

static void navigate_wifi(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    screen_pages_navigate(a,PAGE_WIFI,SCREEN_SLIDE_NONE);
}

static void navigate_api(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    screen_pages_navigate(a,PAGE_API,SCREEN_SLIDE_NONE);
}

static void led_test_cb(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    if(a->interact) {
        screen_interact_set_leds_rgb(a->interact,0,0x39,0xe6,0x9d,40);
        a->interact_leds_off_us=esp_timer_get_time()+1500000;
    }
}

static void reboot_cb(lv_event_t *e)
{
    bsp_display_brightness_set(0);
    vTaskDelay(pdMS_TO_TICKS(200));
    esp_restart();
}

static void brightness_slider_cb(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    lv_obj_t *slider=lv_event_get_target_obj(e);
    int val=lv_slider_get_value(slider);
    if(val<10) { val=10; }
    if(val>100) { val=100; }
    a->current_brightness=val;
    bsp_display_brightness_set(val);
    screen_activity_kick(a);
    if(a->brightness_label) {
        char buf[32]; snprintf(buf,sizeof(buf),"Brightness: %d%%",val);
        lv_label_set_text(a->brightness_label,buf);
    }
}

#ifndef SCREEN_SIM
static void auto_switch_changed(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    bool automatic=lv_obj_has_state(lv_event_get_target_obj(e),LV_STATE_CHECKED);
    esp_err_t err=screen_preferences_set(a,automatic);
    if(err!=ESP_OK) {
        screen_lock(a); bool saved=a->auto_switch_content; screen_unlock(a);
        if(saved) lv_obj_add_state(a->auto_switch_checkbox,LV_STATE_CHECKED);
        else lv_obj_remove_state(a->auto_switch_checkbox,LV_STATE_CHECKED);
        if(a->preferences_hint) lv_label_set_text(a->preferences_hint,"Save failed. Retry.");
    } else {
        a->auto_switch_shown=automatic;
        if(a->preferences_hint) lv_label_set_text(a->preferences_hint,"Saved. Kept after restart.");
    }
}

static void auto_switch_control(struct screen_app *a,lv_obj_t *root,int x,int y,int width)
{
    a->auto_switch_checkbox=lv_checkbox_create(root);
    lv_checkbox_set_text(a->auto_switch_checkbox,"自动切到最新到达内容 (Auto Switch)");
    lv_obj_set_pos(a->auto_switch_checkbox,x,y); lv_obj_set_width(a->auto_switch_checkbox,width);
    lv_obj_set_style_text_color(a->auto_switch_checkbox,lv_color_hex(0xc5d1de),0);
    screen_lock(a); a->auto_switch_shown=a->auto_switch_content; screen_unlock(a);
    if(a->auto_switch_shown) lv_obj_add_state(a->auto_switch_checkbox,LV_STATE_CHECKED);
    lv_obj_add_event_cb(a->auto_switch_checkbox,auto_switch_changed,LV_EVENT_VALUE_CHANGED,a);
}
#endif

static void scan_click(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    struct wifi_command cmd={.scan=true};
    if(xQueueSend(a->wifi_commands,&cmd,0)!=pdTRUE) {
        screen_lock(a); strcpy(a->wifi_message,"Busy. Try again."); screen_unlock(a);
    }
}

static void network_click(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    lv_obj_t *obj=lv_event_get_target_obj(e);
    strlcpy(a->selected_ssid,lv_label_get_text(lv_obj_get_child(obj,0)),sizeof(a->selected_ssid));
    a->selected_open=(uintptr_t)lv_obj_get_user_data(obj)==1;
    screen_pages_navigate(a,PAGE_PASSWORD,SCREEN_SLIDE_NONE);
}

static void cancel_click(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    screen_pages_navigate(a,PAGE_WIFI,SCREEN_SLIDE_NONE);
}

static void connect_click(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    const char *pw=lv_textarea_get_text(a->password);
    size_t n=strlen(pw);
    if(!a->selected_open && (n<8 || n>63)) { lv_label_set_text(a->text,"Password must be 8-63 characters"); return; }
    struct wifi_command cmd={0}; strlcpy(cmd.ssid,a->selected_ssid,sizeof(cmd.ssid));
    strlcpy(cmd.password,pw,sizeof(cmd.password));
    if(xQueueSend(a->wifi_commands,&cmd,0)==pdTRUE) {
        lv_textarea_set_text(a->password,""); screen_pages_navigate(a,PAGE_WIFI,SCREEN_SLIDE_NONE);
    } else lv_label_set_text(a->text,"Busy. Please retry.");
    memset(cmd.password,0,sizeof(cmd.password));
}

static lv_obj_t *create_status_card(lv_obj_t *parent, const struct status_card_schema *schema)
{
    lv_obj_t *card=lv_obj_create(parent);
    lv_obj_set_pos(card,schema->x,schema->y);
    lv_obj_set_size(card,schema->w,schema->h);
    lv_obj_set_style_bg_color(card,lv_color_hex(schema->bg_hex),0);
    lv_obj_set_style_border_color(card,lv_color_hex(schema->border_hex),0);
    lv_obj_set_style_border_width(card,1,0);
    lv_obj_set_style_radius(card,(schema->w>300)?10:8,0);
    lv_obj_set_style_pad_all(card,0,0);
    lv_obj_remove_flag(card,LV_OBJ_FLAG_SCROLLABLE);

    if(schema->header_text) {
        lv_obj_t *t=label(card,schema->header_text,10,8,schema->w-20);
        lv_obj_set_style_text_color(t,lv_color_hex(schema->header_hex),0);
        lv_obj_set_style_text_font(t,&lv_font_montserrat_14,0);
    }
    return card;
}

static void screen_ui_status_build(struct screen_app *a, lv_obj_t *root)
{
    s_status_ui.dot=lv_obj_create(root);
    lv_obj_set_pos(s_status_ui.dot,24,22); lv_obj_set_size(s_status_ui.dot,12,12);
    lv_obj_set_style_radius(s_status_ui.dot,LV_RADIUS_CIRCLE,0);
    lv_obj_set_style_bg_color(s_status_ui.dot,lv_color_hex(a->connected?0x39e69d:0xe5c07b),0);
    lv_obj_set_style_border_width(s_status_ui.dot,0,0);

    lv_obj_t *title=label(root,"MOSAICO DASHBOARD",46,18,248);
    lv_obj_set_style_text_font(title,&a->ui_font,0);
    screen_ui_draw_page_dots(a,root,0,5);

    /* Hero IP Card */
    static const struct status_card_schema s_hero_schema = {
        .x=18, .y=52, .w=444, .h=124,
        .bg_hex=0x141d27, .border_hex=0x233242, .header_hex=0x758899,
        .header_text="LOCAL ACCESS ADDRESS (LAN IP)"
    };
    lv_obj_t *hero=create_status_card(root,&s_hero_schema);
    s_status_ui.ip_label=label(hero,a->ip[0]?a->ip:"0.0.0.0",14,28,410);
    lv_obj_set_style_text_color(s_status_ui.ip_label,lv_color_hex(0xffffff),0);
    lv_obj_set_style_text_font(s_status_ui.ip_label,&lv_font_montserrat_28,0);

    s_status_ui.wifi_label=label(hero,"Wi-Fi: Connecting...",14,82,230);
    lv_obj_set_style_text_color(s_status_ui.wifi_label,lv_color_hex(0x4fa3e3),0);
    lv_obj_set_style_text_font(s_status_ui.wifi_label,&lv_font_montserrat_14,0);

    lv_obj_t *ports=label(hero,"REST :80  •  WS :81",250,82,180);
    lv_obj_set_style_text_color(ports,lv_color_hex(0x8fa3b8),0);
    lv_obj_set_style_text_font(ports,&lv_font_montserrat_14,0);

    /* Middle 2 Cards */
    static const struct status_card_schema s_pwr_schema = {
        .x=18, .y=186, .w=216, .h=114,
        .bg_hex=0x101720, .border_hex=0x1c2b38, .header_hex=0xe5c07b,
        .header_text=LV_SYMBOL_CHARGE " POWER & THERMAL"
    };
    lv_obj_t *card_pwr=create_status_card(root,&s_pwr_schema);
    s_status_ui.power_label=label(card_pwr,"Voltage: --\nCurrent: --\nTemp: --",10,32,196);
    lv_obj_set_style_text_color(s_status_ui.power_label,lv_color_hex(0xc5d1de),0);
    lv_obj_set_style_text_font(s_status_ui.power_label,&lv_font_montserrat_14,0);

    static const struct status_card_schema s_sns_schema = {
        .x=246, .y=186, .w=216, .h=114,
        .bg_hex=0x101720, .border_hex=0x1c2b38, .header_hex=0x4fa3e3,
        .header_text=LV_SYMBOL_GPS " SENSORS & IMU"
    };
    lv_obj_t *card_sns=create_status_card(root,&s_sns_schema);
    s_status_ui.sensor_label=label(card_sns,"IMU: OK\nDown: Type-C\nSubboard: OK",10,32,196);
    lv_obj_set_style_text_color(s_status_ui.sensor_label,lv_color_hex(0xc5d1de),0);
    lv_obj_set_style_text_font(s_status_ui.sensor_label,&lv_font_montserrat_14,0);

    /* Engine Specs Card */
    static const struct status_card_schema s_eng_schema = {
        .x=18, .y=308, .w=444, .h=80,
        .bg_hex=0x101720, .border_hex=0x1c2b38, .header_hex=0x39e69d,
        .header_text=LV_SYMBOL_DRIVE " SYSTEM & SPECS"
    };
    lv_obj_t *card_eng=create_status_card(root,&s_eng_schema);
    char ebuf[128];
    snprintf(ebuf,sizeof(ebuf),"LAN Screen v%s • 480x480 @ 30 FPS\nDual-Core ESP32-S31 • 8MB PSRAM (Healthy)",esp_app_get_description()->version);
    s_status_ui.engine_label=label(card_eng,ebuf,10,30,420);
    lv_obj_set_style_text_color(s_status_ui.engine_label,lv_color_hex(0x8fa3b8),0);
    lv_obj_set_style_text_font(s_status_ui.engine_label,&lv_font_montserrat_14,0);

    /* Bottom Action Bar: Sleek Capsule & Home Indicator */
    lv_obj_t *home_btn=button(a,root,LV_SYMBOL_SETTINGS "  Control Center  •  Swipe " LV_SYMBOL_LEFT " " LV_SYMBOL_RIGHT " for Pipeline",18,406,444,36,open_settings_click);
    lv_obj_set_style_bg_color(home_btn,lv_color_hex(0x16222f),0);
    lv_obj_set_style_border_color(home_btn,lv_color_hex(0x283b4e),0);
    lv_obj_set_style_radius(home_btn,18,0);
    lv_obj_t *home_bar=lv_obj_create(root);
    lv_obj_set_pos(home_bar,200,472);
    lv_obj_set_size(home_bar,80,4);
    lv_obj_set_style_bg_color(home_bar,lv_color_hex(0x2d3e52),0);
    lv_obj_set_style_bg_opa(home_bar,LV_OPA_COVER,0);
    lv_obj_set_style_radius(home_bar,2,0);
    lv_obj_set_style_border_width(home_bar,0,0);
    lv_obj_remove_flag(home_bar,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(home_bar,LV_OBJ_FLAG_CLICKABLE);
}

static void screen_ui_status_refresh(struct screen_app *a)
{
    screen_lock(a);
    bool conn=a->connected;
    char ip[16], ssid[33];
    strlcpy(ip, a->ip, sizeof(ip));
    strlcpy(ssid, a->ssid[0]?a->ssid:"No Wi-Fi", sizeof(ssid));
    int v_mv = a->sensors.battery.voltage_mv;
    int i_ma = a->sensors.battery.current_ma;
    int soc = a->sensors.battery.state_of_charge;
    float temp = a->sensors.battery.temperature_c;
    bool bat_ok = a->sensors.battery_ok;
    bool imu_ok = a->sensors.imu_ok;
    int rot = a->display_rotation_cw_deg;
    const char *face = a->sensors.orientation.valid ? screen_face_name(a->sensors.orientation.down_face) : "Stable";
    float fps = a->fps;
    screen_unlock(a);

    if(s_status_ui.dot) lv_obj_set_style_bg_color(s_status_ui.dot, lv_color_hex(conn ? 0x39e69d : 0xe5c07b), 0);
    if(s_status_ui.ip_label) lv_label_set_text(s_status_ui.ip_label, ip[0] ? ip : "0.0.0.0");
    if(s_status_ui.wifi_label) {
        char buf[48]; snprintf(buf, sizeof(buf), "Wi-Fi: %s", ssid);
        lv_label_set_text(s_status_ui.wifi_label, buf);
    }
    if(s_status_ui.power_label) {
        char buf[128];
        if(bat_ok) {
            const char *st = (i_ma > 15) ? "Charging" : ((i_ma < -15) ? "Discharge" : "Idle");
            snprintf(buf, sizeof(buf), "Battery: %d%% (%d mV)\nRate: %+d mA (%s)\nTemp: %.1f °C",
                     soc, v_mv, i_ma, st, temp);
        } else {
            snprintf(buf, sizeof(buf), "Power: USB 5V Only\nVoltage: %d mV\nTemp: %.1f °C", v_mv, temp);
        }
        lv_label_set_text(s_status_ui.power_label, buf);
    }
    if(s_status_ui.sensor_label) {
        char buf[96];
        snprintf(buf, sizeof(buf), "IMU: %s (%d°)\nDown: %s\nSubboard: Detected", imu_ok ? "6-Axis OK" : "N/A", rot, face);
        lv_label_set_text(s_status_ui.sensor_label, buf);
    }
    if(s_status_ui.engine_label) {
        char buf[128];
        snprintf(buf, sizeof(buf), "LAN Screen v%s • 480x480 @ %.0f FPS\nDual-Core ESP32-S31 • 8MB PSRAM (Healthy)", esp_app_get_description()->version, fps);
        lv_label_set_text(s_status_ui.engine_label, buf);
    }
}

static void screen_ui_home_empty_build(struct screen_app *a, lv_obj_t *root)
{
    lv_obj_t *dot=lv_obj_create(root);
    lv_obj_set_pos(dot,24,22); lv_obj_set_size(dot,12,12);
    lv_obj_set_style_radius(dot,LV_RADIUS_CIRCLE,0);
    lv_obj_set_style_bg_color(dot,lv_color_hex(0x4fa3e3),0);
    lv_obj_set_style_border_width(dot,0,0);

    lv_obj_t *title=label(root,"MEDIA STREAM",46,18,248);
    lv_obj_set_style_text_font(title,&a->ui_font,0);
    screen_ui_draw_page_dots(a,root,2,5);

    lv_obj_t *card=lv_obj_create(root);
    lv_obj_set_pos(card,18,56); lv_obj_set_size(card,444,328);
    lv_obj_set_style_bg_color(card,lv_color_hex(0x141d27),0);
    lv_obj_set_style_border_color(card,lv_color_hex(0x233242),0);
    lv_obj_set_style_border_width(card,1,0);
    lv_obj_set_style_radius(card,10,0);
    lv_obj_set_style_pad_all(card,16,0);
    lv_obj_remove_flag(card,LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *h=label(card,LV_SYMBOL_IMAGE "  Awaiting Media Stream",12,16,400);
    lv_obj_set_style_text_font(h,&lv_font_montserrat_20,0);
    lv_obj_set_style_text_color(h,lv_color_hex(0xffffff),0);

    char desc[256];
    snprintf(desc,sizeof(desc),
        "No photos or frames in RAM history.\n\n"
        "Send JPEG photos or MJPEG stream to:\n"
        "POST http://%s/api/frame\n\n"
        "• Supports Baseline JPEG up to 480x480\n"
        "• Drag & drop from Web Console\n"
        "• 16-frame cyclic rolling history\n"
        "• Pull top for Control Center",
        a->ip[0]?a->ip:"<IP>");
    lv_obj_t *body=label(card,desc,12,56,400);
    lv_obj_set_style_text_color(body,lv_color_hex(0x8fa3b8),0);
    lv_obj_set_style_text_font(body,&lv_font_montserrat_14,0);

    lv_obj_t *media_btn=button(a,root,LV_SYMBOL_SETTINGS "  Control Center  •  Swipe " LV_SYMBOL_LEFT " " LV_SYMBOL_RIGHT " for Pipeline",18,406,444,36,open_settings_click);
    lv_obj_set_style_bg_color(media_btn,lv_color_hex(0x16222f),0);
    lv_obj_set_style_border_color(media_btn,lv_color_hex(0x283b4e),0);
    lv_obj_set_style_radius(media_btn,18,0);
    lv_obj_t *media_home_bar=lv_obj_create(root);
    lv_obj_set_pos(media_home_bar,200,472);
    lv_obj_set_size(media_home_bar,80,4);
    lv_obj_set_style_bg_color(media_home_bar,lv_color_hex(0x2d3e52),0);
    lv_obj_set_style_bg_opa(media_home_bar,LV_OPA_COVER,0);
    lv_obj_set_style_radius(media_home_bar,2,0);
    lv_obj_set_style_border_width(media_home_bar,0,0);
    lv_obj_remove_flag(media_home_bar,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(media_home_bar,LV_OBJ_FLAG_CLICKABLE);
}

static void screen_ui_settings_build(struct screen_app *a, lv_obj_t *root)
{
    label(root,"CONTROL CENTER",24,18,260);
    button(a,root,"< Back",350,14,106,38,home_click);

    /* Display Card */
    lv_obj_t *card1=lv_obj_create(root);
    lv_obj_set_pos(card1,18,60); lv_obj_set_size(card1,444,136);
    lv_obj_set_style_bg_color(card1,lv_color_hex(0x141d27),0);
    lv_obj_set_style_border_color(card1,lv_color_hex(0x233242),0);
    lv_obj_set_style_border_width(card1,1,0);
    lv_obj_set_style_radius(card1,10,0);
    lv_obj_set_style_pad_all(card1,0,0);
    lv_obj_remove_flag(card1,LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *t1=label(card1,LV_SYMBOL_EYE_OPEN " DISPLAY & BACKLIGHT",14,10,410);
    lv_obj_set_style_text_color(t1,lv_color_hex(0x4fa3e3),0);
    lv_obj_set_style_text_font(t1,&lv_font_montserrat_14,0);

    char bbuf[32]; snprintf(bbuf,sizeof(bbuf),"Brightness: %d%%",a->current_brightness?a->current_brightness:80);
    a->brightness_label=label(card1,bbuf,14,32,410);
    lv_obj_set_style_text_color(a->brightness_label,lv_color_hex(0xffffff),0);
    lv_obj_set_style_text_font(a->brightness_label,&lv_font_montserrat_14,0);

    lv_obj_t *slider=lv_slider_create(card1);
    lv_obj_set_pos(slider,14,54); lv_obj_set_size(slider,416,18);
    lv_slider_set_range(slider,10,100);
    lv_slider_set_value(slider,a->current_brightness?a->current_brightness:80,LV_ANIM_OFF);
    lv_obj_add_event_cb(slider,brightness_slider_cb,LV_EVENT_VALUE_CHANGED,a);

#ifndef SCREEN_SIM
    auto_switch_control(a,card1,14,82,416);
    lv_obj_t *dim_hint=label(card1,"Auto-dim: 2 min • Sleep: 15 min (Touch/API wakes up)",14,112,416);
    lv_obj_set_style_text_color(dim_hint,lv_color_hex(0x607285),0);
    lv_obj_set_style_text_font(dim_hint,&lv_font_montserrat_14,0);
#endif

    /* Tools Card */
    lv_obj_t *card2=lv_obj_create(root);
    lv_obj_set_pos(card2,18,206); lv_obj_set_size(card2,444,154);
    lv_obj_set_style_bg_color(card2,lv_color_hex(0x141d27),0);
    lv_obj_set_style_border_color(card2,lv_color_hex(0x233242),0);
    lv_obj_set_style_border_width(card2,1,0);
    lv_obj_set_style_radius(card2,10,0);
    lv_obj_set_style_pad_all(card2,0,0);
    lv_obj_remove_flag(card2,LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *t2=label(card2,LV_SYMBOL_SETTINGS " HARDWARE & TOOLS",14,10,410);
    lv_obj_set_style_text_color(t2,lv_color_hex(0xe5c07b),0);
    lv_obj_set_style_text_font(t2,&lv_font_montserrat_14,0);

    button(a,card2,"Wi-Fi Setup",14,34,200,44,navigate_wifi);
    button(a,card2,"Subboard LED",230,34,200,44,led_test_cb);
    button(a,card2,"API Guide",14,90,200,44,navigate_api);
    button(a,card2,"Reboot Device",230,90,200,44,reboot_cb);

    button(a,root,"< Tap or Swipe Up to Return >",18,372,444,54,home_click);
}

void screen_ui_build(struct screen_app *a)
{
    screen_ui_messages_remember(a);
    if(a->password) lv_textarea_set_text(a->password,"");
    a->password=NULL; a->keyboard=NULL; a->text=NULL;
    memset(&s_status_ui, 0, sizeof(s_status_ui));
#ifndef SCREEN_SIM
    a->message_notice=NULL; a->auto_switch_checkbox=NULL; a->preferences_hint=NULL;
    a->notice_unread=UINT32_MAX;
    a->notice_image_unread=UINT32_MAX;
#endif
    lv_obj_t *root=lv_screen_active(); lv_obj_clean(root);
    lv_obj_set_style_bg_color(root,lv_color_hex(0x101720),0);
    lv_obj_set_style_text_color(root,lv_color_hex(0xf0f4fa),0);
    if(!a->ui_font_ready) { a->ui_font=lv_font_montserrat_20; a->ui_font.fallback=&screen_font_cjk_16; a->ui_font_ready=true; }
    lv_obj_set_style_text_font(root,&a->ui_font,0);
    lv_obj_remove_flag(root,LV_OBJ_FLAG_SCROLLABLE);
    a->stream_visible=false;
    a->text_list=NULL; a->card_count=0;
    a->messages_empty=NULL;
    a->widget_header_title=NULL; a->widget_list_box=NULL;

    if(a->page==PAGE_STATUS) { screen_ui_status_build(a,root); return; }
    if(a->page==PAGE_WIDGET) { screen_ui_widget_build(a,root); return; }
    if(a->page==PAGE_TEXT) { screen_ui_messages_build(a,root); return; }
    if(a->page==PAGE_SETTINGS) { screen_ui_settings_build(a,root); return; }
    if(a->page==PAGE_HOME) { screen_ui_home_empty_build(a,root); return; }

    const char *titles[]={"STATUS","WIDGET","MEDIA","MESSAGES","CAMERA","Settings","Wi-Fi","Join network","Metrics","Sensors","API Guide","Settings"};
    lv_obj_t *title=label(root,titles[a->page],24,28,a->page==PAGE_CAMERA?250:432);
    lv_obj_set_style_text_font(title,&lv_font_montserrat_28,0);
    if(a->page==PAGE_WIFI) { lv_obj_set_pos(title,134,26); lv_obj_set_width(title,200); }
    if(a->page==PAGE_PASSWORD) lv_obj_add_flag(title,LV_OBJ_FLAG_HIDDEN);

    if(a->page==PAGE_CAMERA) {
        screen_ui_draw_page_dots(a,root,4,5);
        label(root,"< Swipe " LV_SYMBOL_LEFT " " LV_SYMBOL_RIGHT " Pipeline / Media / Messages >",24,447,432);
    } else {
        button(a,root,"< Tap or Swipe Up to Return >",24,435,432,38,home_click);
    }

    if(a->page==PAGE_WIFI) {
        button(a,root,"< Back",24,20,96,44,home_click);
        button(a,root,"Scan",346,20,110,44,scan_click);
        a->text=label(root,"",24,76,432);
        lv_obj_t *list=lv_obj_create(root); lv_obj_set_pos(list,16,114); lv_obj_set_size(list,448,304);
        lv_obj_set_style_bg_color(list,lv_color_hex(0x1c2836),0);
        wifi_ap_record_t *aps=heap_caps_malloc(sizeof(a->aps),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
        if(aps) {
            screen_lock(a);unsigned count=a->ap_count;memcpy(aps,a->aps,sizeof(a->aps));a->rendered_generation=a->scan_generation;screen_unlock(a);
            for(unsigned i=0;i<count;i++) {
                if(!aps[i].ssid[0])continue;
                lv_obj_t *b=button(a,list,(char*)aps[i].ssid,4,i*62,404,54,network_click);
                lv_obj_set_user_data(b,(void*)(uintptr_t)(aps[i].authmode==WIFI_AUTH_OPEN?1:2));
            }
            free(aps);
        } else lv_label_set_text(a->text,"Not enough memory to display networks. Retry Scan.");
    } else if(a->page==PAGE_PASSWORD) {
        button(a,root,"< Back",24,18,90,44,cancel_click);
        a->text=label(root,a->selected_ssid,124,24,332);
        a->password=lv_textarea_create(root); lv_obj_set_pos(a->password,24,76); lv_obj_set_size(a->password,220,48);
        lv_textarea_set_one_line(a->password,true); lv_textarea_set_password_mode(a->password,true);
        lv_textarea_set_max_length(a->password,63); lv_textarea_set_placeholder_text(a->password,a->selected_open?"Open network":"Password");
        button(a,root,"Join",254,76,100,48,connect_click);
        button(a,root,"Cancel",362,76,94,48,cancel_click);
        a->keyboard=lv_keyboard_create(root); lv_obj_set_size(a->keyboard,480,224); lv_obj_align(a->keyboard,LV_ALIGN_TOP_LEFT,0,206);
        lv_obj_add_event_cb(a->keyboard,connect_click,LV_EVENT_READY,a);
        lv_keyboard_set_mode(a->keyboard,LV_KEYBOARD_MODE_TEXT_LOWER); lv_keyboard_set_textarea(a->keyboard,a->password);
    } else {
        a->text=label(root,"",24,110,432);
    }
    lv_obj_invalidate(root);
}

void screen_ui_refresh(struct screen_app *a)
{
    screen_ui_refresh_battery(a);
#ifndef SCREEN_SIM
    screen_lock(a); unsigned unread=screen_history_unread(&a->messages);
    unsigned images=screen_history_unread(&a->images);
    bool automatic=a->auto_switch_content; screen_unlock(a);
    if(a->message_notice && (unread!=a->notice_unread || images!=a->notice_image_unread)) {
        a->notice_unread=unread; a->notice_image_unread=images;
        if((a->page==PAGE_TEXT && images) || (a->page!=PAGE_TEXT && (unread || images))) {
            char count[40];
            if(a->page==PAGE_TEXT) snprintf(count,sizeof(count),"图片未读 %u",images);
            else snprintf(count,sizeof(count),"图%u 文%u",images,unread);
            lv_label_set_text(a->message_notice,count);
        } else lv_label_set_text(a->message_notice,"");
    }
    if(a->auto_switch_checkbox && automatic!=a->auto_switch_shown) {
        a->auto_switch_shown=automatic;
        if(automatic) lv_obj_add_state(a->auto_switch_checkbox,LV_STATE_CHECKED);
        else lv_obj_remove_state(a->auto_switch_checkbox,LV_STATE_CHECKED);
    }
#endif
    if(a->page==PAGE_STATUS) { screen_ui_status_refresh(a); return; }
    if(a->page==PAGE_WIDGET) { screen_ui_widget_refresh(a); return; }
    if(a->page==PAGE_TEXT || a->page==PAGE_PASSWORD || a->page==PAGE_SETTINGS || a->page==PAGE_HOME) return;
    if(!a->text) return;

    char text[512]; screen_lock(a);
    switch(a->page) {
    case PAGE_CAMERA:
#ifndef SCREEN_SIM
        screen_unlock(a);screen_camera_render_describe(a->io,text,sizeof(text));lv_label_set_text(a->text,text);return;
#else
        snprintf(text,sizeof(text),"Camera page");break;
#endif
    case PAGE_WIFI: snprintf(text,sizeof(text),"%s",a->wifi_message); break;
    case PAGE_API:
        snprintf(text,sizeof(text),"Guide: http://%s/\n\nGET /api/info, /api/status\nGET /api/sensors, /api/orientation\nGET /api/history, /api/config\nGET /api/widget (Agent Pipeline)\nPOST /api/widget (Agent Step & Confirm)\nGET /api/image?id=N\nPOST /api/frame (JPEG)\nPOST /api/text (JSON)\nPOST /api/view (Switch Page)",a->ip); break;
    case PAGE_METRICS:
        snprintf(text,sizeof(text),"Displayed  %.1f FPS\n\nJPEG decode  %.1f ms\nLCD transfer  %.1f ms\n\nReceived  %lu\nDisplayed  %lu   Replaced  %lu\nInvalid  %lu",a->fps,a->decode_ms,a->present_ms,(unsigned long)a->received,(unsigned long)a->presented,(unsigned long)a->dropped,(unsigned long)a->invalid); break;
    default:
        snprintf(text,sizeof(text),"Down: %s   Auto: %d deg\n\nIMU  %s\nAccel g  %.2f / %.2f / %.2f\nGyro dps  %.1f / %.1f / %.1f\n\nMag 0: %s   Mag 1: %s\nBattery: %s\n%d mV   %d mA   %.1f C",a->sensors.orientation.valid?screen_face_name(a->sensors.orientation.down_face):"unknown",a->display_rotation_cw_deg,a->sensors.imu_ok?"OK":"Unavailable",a->sensors.accel[0],a->sensors.accel[1],a->sensors.accel[2],a->sensors.gyro[0],a->sensors.gyro[1],a->sensors.gyro[2],a->sensors.mag_ok[0]?"OK":"N/A",a->sensors.mag_ok[1]?"OK":"N/A",a->sensors.battery_ok?"OK":"Unavailable",a->sensors.battery.voltage_mv,a->sensors.battery.current_ma,a->sensors.battery.temperature_c); break;
    }
    screen_unlock(a); lv_label_set_text(a->text,text);
}
