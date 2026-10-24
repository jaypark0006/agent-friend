#include "screen_private.h"
#include "screen_renderer.h"
#include "screen_widget.h"
#include "screen_display_driver.h"
#include "screen_camera_service.h"
#include "bsp/esp_mosaico.h"
#include "esp_iris.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "esp_check.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
static void scroll_absolute(void *obj,int32_t y) { lv_obj_scroll_to_y(obj,y,LV_ANIM_OFF); }
void screen_activity_kick(struct screen_app *a)
{
    a->last_activity_us=esp_timer_get_time();
    if(a->display_sleeping || a->display_dimmed) {
        a->display_sleeping=false;
        a->display_dimmed=false;
        a->current_brightness=80;
        bsp_display_brightness_set(80);
    }
}
static void apply_scroll(struct screen_app *a)
{
    screen_lock(a); bool pending=a->scroll_pending;
    int y=a->requested_scroll_y; unsigned ms=a->requested_scroll_ms;
    a->scroll_pending=false; screen_unlock(a);
    if(!pending) return;
    lv_obj_t *view=(a->page==PAGE_TEXT)?a->text_list:(a->page==PAGE_WIDGET)?a->widget_list_box:NULL;
    if(!view) return;
    lv_obj_update_layout(view);
    int limit=lv_obj_get_scroll_y(view)+lv_obj_get_scroll_bottom(view);
    if(y<0 || y>limit) y=limit;
    lv_anim_delete(view,scroll_absolute);
    if(!ms) { scroll_absolute(view,y); return; }
    lv_anim_t anim; lv_anim_init(&anim); lv_anim_set_var(&anim,view);
    lv_anim_set_exec_cb(&anim,scroll_absolute);
    lv_anim_set_values(&anim,lv_obj_get_scroll_y(view),y);
    lv_anim_set_duration(&anim,ms); lv_anim_set_path_cb(&anim,lv_anim_path_linear); lv_anim_start(&anim);
}
static void poll_touch(struct screen_app *a)
{
    int64_t began=esp_timer_get_time();
    uint8_t count=0;
    esp_lcd_touch_point_data_t point={0};
    esp_err_t err=esp_lcd_touch_read_data(a->touch);
    bool valid=err==ESP_OK;
    if(valid) valid=esp_lcd_touch_get_data(a->touch,&point,&count,1)==ESP_OK;
    int64_t elapsed=esp_timer_get_time()-began;
    screen_lock(a); a->touch_polls++; a->touch_total_us+=elapsed;
    if(elapsed>a->touch_max_us) a->touch_max_us=elapsed;
    bool down=valid && count>0;
    if(down!=a->touch_sample.down || (down && (point.x!=a->touch_sample.x || point.y!=a->touch_sample.y))) {
        a->touch_sample.down=down;
        if(down) { a->touch_sample.x=point.x; a->touch_sample.y=point.y; }
        a->touch_sample.timestamp_us=began;
        a->touch_sample.seq++;
    }
    screen_unlock(a);
    if(down) screen_activity_kick(a);
    bool was_down=a->touch_state.down;
    screen_page_t target=screen_touch_update(&a->touch_state,a->page,valid,
        count>0,point.x,point.y,screen_display_tick_ms());
    if(screen_transition_active(a->transition)) { a->touch_state.consumed=true; return; }
    if(!was_down && a->touch_state.down) {
        if(a->text_list) lv_anim_delete(a->text_list,scroll_absolute);
        if(a->widget_list_box) lv_anim_delete(a->widget_list_box,scroll_absolute);
    }
    if(a->touch_state.history_delta) {
        screen_lock(a); bool moved=screen_history_step(&a->images,a->touch_state.history_delta);
        if(moved) screen_history_hide(&a->images);
        screen_unlock(a);
        if(moved) {
            screen_display_wait(a); screen_transition_prepare(a->transition,a->mirror);
            a->transition_preparing=true;
            a->transition_counts_frame=false;
            screen_lock(a); a->transitioning=true; screen_unlock(a);
            a->transition_direction=a->touch_state.history_delta>0?SCREEN_SLIDE_UP:SCREEN_SLIDE_DOWN;
        }
    }
    if(target==PAGE_HOME && !screen_is_main(a->page)) target=a->main_page;
    if(target!=a->page) {
        /* Clear a pressed LVGL object before deleting its page. */
        lv_indev_reset(a->indev,NULL);
        int dx=a->touch_state.x-a->touch_state.start_x;
        int dy=a->touch_state.y-a->touch_state.start_y;
        a->transition_direction=abs(dx)>abs(dy)?(dx<0?SCREEN_SLIDE_LEFT:SCREEN_SLIDE_RIGHT):(dy<0?SCREEN_SLIDE_UP:SCREEN_SLIDE_DOWN);
        screen_pages_navigate(a,target,a->transition_direction);
    }
}
static void replay_picture(struct screen_app *a)
{
    screen_display_wait(a);
    if(a->transition_preparing) {
        screen_mirror_write(a->mirror,0,0,480,480,a->pixels[a->output_index^1]);
        a->stream_visible=true; return;
    }
    a->dma_frame=false;
    ESP_ERROR_CHECK(esp_lcd_panel_draw_bitmap(a->panel,0,0,480,480,a->pixels[a->output_index^1]));
    a->dma_mirror=a->pixels[a->output_index^1];
    a->dma_busy=true; a->stream_visible=true;
}
static void rotate_display(struct screen_app *a)
{
    if(a->transition_preparing || screen_transition_active(a->transition)) return;
    int64_t now=esp_timer_get_time();
    screen_lock(a);
    int current=a->display_rotation_cw_deg;
    /* All pages keep gravity-based UI/touch orientation. Camera pixels apply
     * a separate mounting correction and inverse of this actual panel angle. */
    a->auto_rotation_cw_deg=screen_rotation_select(a->auto_rotation_cw_deg,&a->sensors.orientation,
        a->sensors.timestamp_us,now,a->touch_state.down);
    int target=a->auto_rotation_cw_deg;
    screen_unlock(a);
    if(target==current || now<a->rotation_retry_us) return;
    /* Drain our raw DMA; BSP drains only its optional LVGL adapter. MADCTL
     * rotates pixels in hardware and BSP applies the inverse touch mapping. */
    screen_display_wait(a);
    esp_err_t err=bsp_display_set_rotation((bsp_display_rotation_t)target);
    if(err!=ESP_OK) {
        a->rotation_retry_us=now+1000000;
        ESP_LOGW("display","rotation deferred: %s",esp_err_to_name(err));
        return;
    }
    lv_indev_reset(a->indev,NULL);
    memset(&a->touch_state,0,sizeof(a->touch_state));
    screen_lock(a); a->display_rotation_cw_deg=target; screen_unlock(a);
    if(a->page==PAGE_CAMERA && a->have_frame) {
        uint8_t *front=a->pixels[a->output_index^1];
        a->have_frame=screen_camera_render_redraw(a->io,front,screen_camera_frame_rotation(target));
        if(a->have_frame) screen_renderer_badge(a,front);
        else a->stream_visible=false;
    }
    if((a->page==PAGE_HOME || a->page==PAGE_CAMERA) && a->have_frame) replay_picture(a);
    else { lv_obj_invalidate(lv_screen_active()); lv_refr_now(a->display); screen_display_wait(a); }
}
void screen_display_task(void *ctx)
{
    struct screen_app *a=ctx;
    a->last_activity_us=esp_timer_get_time();
    a->current_brightness=80;
    a->display_dimmed=false;
    a->display_sleeping=false;
    screen_display_wait(a); screen_ui_build(a); screen_ui_refresh(a); lv_refr_now(a->display); screen_display_wait(a);
    screen_mirror_tick(a->mirror);
    bool marked_healthy=false;
    int64_t ui_time=0, fps_time=esp_timer_get_time(); uint32_t fps_count=0, gui_fps_count=0;
    while(true) {
        unsigned sleep_ms=a->touch_state.down?1:5;
        screen_lock(a); bool ready=a->startup_ready; screen_unlock(a);
        if(ready && !marked_healthy) { ESP_ERROR_CHECK(esp_iris_mark_healthy()); marked_healthy=true; }
        poll_touch(a);
        rotate_display(a);
        if(screen_transition_active(a->transition)) {
            const uint8_t *frame=NULL;
            /* The compositor reuses its DMA frame only after completion. */
            screen_display_wait(a);
            if(screen_transition_next(a->transition,esp_timer_get_time(),&frame)) {
                bool final=!screen_transition_active(a->transition);
                a->dma_frame=final && a->transition_counts_frame;
                a->frame_received_us=a->transition_received_us;
                if(final) a->transition_counts_frame=false;
                a->dma_start_us=esp_timer_get_time();
                ESP_ERROR_CHECK(esp_lcd_panel_draw_bitmap(a->panel,0,0,480,480,frame));
                a->dma_mirror=frame; a->dma_busy=true;
                if(final) {
                    screen_display_wait(a);
                    screen_lock(a); a->transitioning=false;
                    screen_unlock(a);screen_pages_presented(a);
                }
            }
            if(!a->dma_busy || screen_mirror_requested(a->mirror)) {
                screen_display_wait(a); screen_mirror_tick(a->mirror);
            }
            vTaskDelay(pdMS_TO_TICKS(5)); continue;
        }
        /* Pushes focus their page after a gesture/momentum finishes. Keep
         * settings and password entry open; the latest request wins on exit.
         * Explicit /api/view requests remain immediate. */
        bool allow_push=screen_is_main(a->next_page) && !a->touch_state.down &&
            !(a->page==PAGE_TEXT && a->text_list && lv_obj_is_scrolling(a->text_list)) &&
            !(a->page==PAGE_WIDGET && a->widget_list_box && lv_obj_is_scrolling(a->widget_list_box));
        screen_pages_resolve(a,allow_push);
        if(a->page!=a->next_page) {
            if(!a->transition_preparing) {
                screen_display_wait(a); screen_transition_prepare(a->transition,a->mirror);
                a->transition_preparing=true;
                a->transition_counts_frame=false;
                screen_lock(a); a->transitioning=true; screen_unlock(a);
            }
            if(a->transition_direction==SCREEN_SLIDE_NONE)
                a->transition_direction=a->next_page==PAGE_SETTINGS?SCREEN_SLIDE_DOWN:
                    !screen_is_main(a->page) && screen_is_main(a->next_page)?SCREEN_SLIDE_UP:
                    a->next_page==PAGE_HOME?SCREEN_SLIDE_RIGHT:SCREEN_SLIDE_LEFT;
            bool scan=a->next_page==PAGE_WIFI && a->page!=PAGE_PASSWORD;
            if(a->page==PAGE_WIDGET && a->widget_list_box) {
                int y=lv_obj_get_scroll_y(a->widget_list_box),maximum=y+lv_obj_get_scroll_bottom(a->widget_list_box);
                screen_lock(a); a->widget_scroll_y=y; a->widget_scroll_max=maximum; a->widget_scroll_saved=true; screen_unlock(a);
            }
            screen_display_wait(a);screen_pages_commit(a);screen_ui_build(a);screen_ui_refresh(a);
            lv_obj_invalidate(lv_screen_active()); lv_refr_now(a->display);
            if(a->page==PAGE_HOME && a->have_frame) {
                replay_picture(a);
            }
            if(scan) { struct wifi_command cmd={.scan=true}; xQueueSend(a->wifi_commands,&cmd,0); }
        }
        screen_lock(a);
        unsigned text_generation=a->messages.generation;
        screen_unlock(a);
        if(a->page==PAGE_TEXT && (a->text_reveal_id || a->text_generation!=text_generation) && !a->touch_state.down && !lv_obj_is_scrolling(a->text_list)) {
            screen_display_wait(a);screen_ui_messages_sync(a);
        }
        if(!a->transition_preparing) apply_scroll(a);
        int64_t now=esp_timer_get_time();
        if(now-fps_time>=1000000) {
            screen_lock(a); a->gui_fps=(a->gui_refreshes-gui_fps_count)*1000000.0f/(now-fps_time); gui_fps_count=a->gui_refreshes; a->fps=(a->presented-fps_count)*1000000.0f/(now-fps_time); fps_count=a->presented; screen_unlock(a); fps_time=now;
        }
        screen_lock(a); unsigned generation=a->scan_generation; screen_unlock(a);
        if(a->page==PAGE_WIFI && a->rendered_generation!=generation) { screen_display_wait(a); screen_ui_build(a); }
        bool camera_live=a->page==PAGE_CAMERA && screen_camera_service_live(a->io);
        if(a->page==PAGE_CAMERA && !camera_live && a->stream_visible) {
            screen_display_wait(a);a->have_frame=false;a->stream_visible=false;
            screen_ui_refresh(a);lv_obj_invalidate(lv_screen_active());
        }
        screen_rendered_frame_t rendered={0};
        if(screen_renderer_prepare(a,&rendered)) {
                unsigned idx=a->output_index;
                screen_display_wait(a);
                a->image_display_id=rendered.history_id;a->rendered_image_id=rendered.camera?0:rendered.selected_id;
                screen_lock(a); screen_history_hide(&a->images); screen_unlock(a);
                screen_renderer_badge(a,a->pixels[idx]);
                if(a->transition_preparing) {
                    screen_mirror_write(a->mirror,0,0,480,480,a->pixels[idx]);
                    a->transition_counts_frame=rendered.counts_frame;a->transition_received_us=rendered.received_us;
                }
                else {
                    a->dma_start_us=esp_timer_get_time(); a->dma_frame=rendered.counts_frame;a->dma_camera=rendered.camera;a->frame_received_us=rendered.received_us;
                    ESP_ERROR_CHECK(esp_lcd_panel_draw_bitmap(a->panel,0,0,480,480,a->pixels[idx]));
                    a->dma_mirror=a->pixels[idx]; a->dma_busy=true;
                }
                a->output_index^=1; a->stream_visible=true; a->have_frame=true;
        } else if((a->page!=PAGE_HOME && a->page!=PAGE_CAMERA) || !a->stream_visible) {
            if(now-ui_time>250000) {
                screen_ui_refresh(a); ui_time=now;
                if(a->text_list) {
                    int y=lv_obj_get_scroll_y(a->text_list),maximum=y+lv_obj_get_scroll_bottom(a->text_list);
                    screen_lock(a); a->text_scroll_y=y; a->text_scroll_max=maximum; screen_unlock(a);
                }
                if(a->widget_list_box) {
                    int y=lv_obj_get_scroll_y(a->widget_list_box),maximum=y+lv_obj_get_scroll_bottom(a->widget_list_box);
                    screen_lock(a); a->widget_scroll_y=y; a->widget_scroll_max=maximum; a->widget_scroll_saved=true; screen_unlock(a);
                }
            }
            unsigned next=screen_display_gui_step(a);
            if(next<sleep_ms) sleep_ms=next;
            if(!a->transition_preparing) screen_ui_read_tick(a,esp_timer_get_time(),a->touch_state.down);
        }
        if(a->interact) {
            if(a->interact_leds_off_us>0 && now>=a->interact_leds_off_us) {
                screen_interact_set_leds_rgb(a->interact, 1, 0, 0, 0, 0);
                a->interact_leds_off_us=0;
            }
            static uint32_t s_last_interact_seq[2] = {0, 0};
            static bool s_prev_motion[2] = {false, false};
            static bool s_prev_left[2] = {false, false};
            static bool s_prev_right[2] = {false, false};
            for(unsigned slot = 0; slot < 2; slot++) {
                mosaico_interact_inputs_t in;
                uint32_t seq = 0;
                if(screen_interact_get_inputs(a->interact, slot, &in, &seq) == ESP_OK) {
                    if(seq != s_last_interact_seq[slot]) {
                        s_last_interact_seq[slot] = seq;
                        if(in.motion_detected && !s_prev_motion[slot]) {
                            screen_activity_kick(a);
                        }
                        s_prev_motion[slot] = in.motion_detected;

                        if(in.left_pressed && !s_prev_left[slot]) {
                            screen_activity_kick(a);
                            if(a->page == PAGE_WIDGET) {
                                screen_widget_trigger_action(a, 1);
                            }
                        }
                        if(in.right_pressed && !s_prev_right[slot]) {
                            screen_activity_kick(a);
                            if(a->page == PAGE_WIDGET) {
                                screen_widget_trigger_action(a, 2);
                            }
                        }
                        s_prev_left[slot] = in.left_pressed;
                        s_prev_right[slot] = in.right_pressed;
                    }
                }
            }
        }
        int64_t idle_us=now-a->last_activity_us;
        if(!a->display_sleeping && idle_us>=900000000LL) {
            a->display_sleeping=true;
            a->current_brightness=0;
            bsp_display_brightness_set(0);
        } else if(!a->display_sleeping && !a->display_dimmed && idle_us>=120000000LL) {
            a->display_dimmed=true;
            a->current_brightness=20;
            bsp_display_brightness_set(20);
        } else if(a->page==PAGE_HOME) {
            screen_display_wait(a); bool changed=false;
            screen_lock(a); int i=screen_history_find(&a->images,a->image_display_id);
            if(i>=0 && !a->touch_state.down && !a->transition_preparing) changed=screen_entry_expose(&a->images.entries[i],0,480,480,now);
            else screen_history_hide(&a->images);
            if(a->image_notice_unread!=screen_history_unread(&a->messages)) changed=true;
            screen_unlock(a);
            if(changed) { screen_renderer_badge(a,a->pixels[a->output_index^1]); replay_picture(a); }
        }
        if(a->transition_preparing) {
            screen_display_wait(a);
            screen_transition_start(a->transition,a->mirror,a->transition_direction,esp_timer_get_time());
            a->transition_preparing=false; a->transition_direction=SCREEN_SLIDE_NONE;
        } else if(!a->dma_busy || screen_mirror_requested(a->mirror)) {
            screen_display_wait(a); screen_mirror_tick(a->mirror);
        }
        if(!a->dma_busy && !screen_transition_active(a->transition))screen_pages_presented(a);
        vTaskDelay(pdMS_TO_TICKS(sleep_ms?sleep_ms:1));
    }
}
