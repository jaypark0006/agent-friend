#include "screen_private.h"
#include "esp_log.h"
#include "screen_pages.h"
#include "screen_camera_service.h"

void screen_pages_cancel_arrival_locked(screen_app_handle_t a)
{
    a->auto_focus_pending=false;a->auto_focus_id=0;
}
void screen_pages_request_locked(screen_app_handle_t a,screen_page_t page)
{
    a->requested_page=page;a->view_pending=true;screen_pages_cancel_arrival_locked(a);
}
void screen_pages_arrival_locked(screen_app_handle_t a,screen_page_t page,uint32_t id)
{
    if(!a->auto_switch_content)return;
    if(page==PAGE_HOME && a->active_page==PAGE_HOME && a->images.follow_latest && !a->auto_focus_pending)return;
    a->auto_focus_page=page;a->auto_focus_id=id;a->auto_focus_pending=true;
}
void screen_pages_navigate(screen_app_handle_t a,screen_page_t page,screen_slide_t direction)
{
    a->next_page=page;a->transition_direction=direction;
}
void screen_pages_resolve(screen_app_handle_t a,bool allow_push)
{
    bool restart_camera=false;
    screen_lock(a);
    if(a->view_pending) {
        restart_camera=a->page==PAGE_CAMERA && a->requested_page==PAGE_CAMERA;
        screen_pages_navigate(a,a->requested_page,SCREEN_SLIDE_NONE);
        a->text_reveal_id=0;a->view_pending=false;
    } else if(a->auto_focus_pending && allow_push) {
        screen_pages_navigate(a,a->auto_focus_page,SCREEN_SLIDE_NONE);
        a->text_reveal_id=a->auto_focus_page==PAGE_TEXT?a->auto_focus_id:0;
        if(a->auto_focus_page==PAGE_HOME) {
            a->images.follow_latest=true;
            if(a->images.count)a->images.selected_id=a->images.entries[screen_history_at(&a->images,a->images.count-1)].id;
            a->images.generation++;
        }
        screen_pages_cancel_arrival_locked(a);a->scroll_pending=false;
    }
    screen_unlock(a);
    if(restart_camera)screen_camera_service_page(a->io,true);
}
void screen_pages_commit(screen_app_handle_t a)
{
    if(a->page==a->next_page)return;
    if(a->next_page==PAGE_CAMERA || a->page==PAGE_CAMERA) {
        esp_err_t error=screen_camera_service_page(a->io,a->next_page==PAGE_CAMERA);
        if(error!=ESP_OK)ESP_LOGW("pages","camera page: %s",esp_err_to_name(error));
        a->have_frame=false;a->rendered_image_id=0;a->image_display_id=0;
    }
    a->page=a->next_page;
    if(screen_is_main(a->page))a->main_page=a->page;
    screen_lock(a);a->active_page=a->page;
    screen_history_hide(&a->images);screen_history_hide(&a->messages);screen_unlock(a);
}
void screen_pages_presented(screen_app_handle_t a)
{
    screen_lock(a);a->displayed_is_text=a->page==PAGE_TEXT;a->displayed_page=a->page;
    if(screen_is_main(a->page))a->displayed_content_generation=a->page==PAGE_TEXT?a->text_generation:a->page==PAGE_CAMERA?0:a->image_display_id;
    screen_unlock(a);
}
