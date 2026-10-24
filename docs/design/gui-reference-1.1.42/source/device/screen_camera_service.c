#include "screen_io_private.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include <stdlib.h>

const char *screen_camera_phase_name(screen_camera_phase_t phase)
{
    switch(phase) {
    case SCREEN_CAMERA_STARTING:return "starting";
    case SCREEN_CAMERA_RUNNING:return "running";
    case SCREEN_CAMERA_STOPPING:return "stopping";
    case SCREEN_CAMERA_ERROR:return "error";
    default:return "idle";
    }
}
static esp_err_t ensure_render_pool(screen_io_handle_t io)
{
    /* camera_control serializes initialization. Capture/display can only use
     * these boot-lifetime buffers after enabled is published under io lock. */
    if(io->render.latest)return ESP_OK;
    for(unsigned i=0;i<SCREEN_CAMERA_RENDER_SLOTS;i++) {
        io->render.slots[i].pixels=heap_caps_malloc(SCREEN_CAMERA_RENDER_BYTES,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
        if(!io->render.slots[i].pixels)goto fail;
    }
    io->render.latest=heap_caps_malloc(SCREEN_CAMERA_RENDER_BYTES,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    if(io->render.latest)return ESP_OK;
fail:
    for(unsigned i=0;i<SCREEN_CAMERA_RENDER_SLOTS;i++){free(io->render.slots[i].pixels);io->render.slots[i].pixels=NULL;}
    return ESP_ERR_NO_MEM;
}
static esp_err_t request(screen_io_handle_t io,bool raw,bool enabled)
{
    xSemaphoreTake(io->camera_control,portMAX_DELAY);
    io_lock(io);bool ready=io->cam.ready;if(!raw)io->camera_page_visible=enabled;bool page_visible=io->camera_page_visible;io_unlock(io);
    bool page_on=enabled && (!raw || page_visible);
    esp_err_t error=enabled && !ready?ESP_ERR_INVALID_STATE:page_on?ensure_render_pool(io):ESP_OK;
    io_lock(io);
    if(error!=ESP_OK) {io->render.error=error;io_unlock(io);xSemaphoreGive(io->camera_control);return error;}
    if(raw) {
        io->camera_raw_requested=enabled;
        if(!enabled)io->camera_page_requested=false; /* explicit global stop */
        else if(page_visible)io->camera_page_requested=true;
    } else {io->camera_page_requested=enabled;io->camera_page_visible=enabled;}
    bool desired=io->camera_raw_requested || io->camera_page_requested;
    bool retry=(enabled || !desired) && io->cam.request_id==io->cam.applied_request_id && ((desired && !io->cam.enabled) || io->cam.error!=ESP_OK);
    if(io->cam.requested!=desired || retry) {
        io->cam.requested=desired;io->cam.request_id++;io->cam.error=ESP_OK;
        io->camera_phase=desired?SCREEN_CAMERA_STARTING:SCREEN_CAMERA_STOPPING;
    }
    struct screen_camera_render *r=&io->render;
    bool render_enabled=io->camera_page_requested;
    if(r->enabled!=render_enabled || retry) {
        r->enabled=render_enabled;r->generation++;r->latest_us=r->next_frame_us=0;
        r->render_fps=r->display_fps=0;r->last_display_us=0;
        r->window_us=r->display_window_us=0;r->window_frames=r->display_window_frames=0;
        for(unsigned i=0;i<SCREEN_CAMERA_RENDER_SLOTS;i++)
            if(r->slots[i].state==CAMERA_RENDER_READY)r->slots[i].state=CAMERA_RENDER_FREE;
    }
    if(!r->target_fps)r->target_fps=30;
    if(!r->block_size)r->block_size=SCREEN_CAMERA_RENDER_DEFAULT_BLOCK_SIZE;
    r->camera_owned=io->camera_page_requested;r->camera_request_id=io->cam.request_id;r->error=ESP_OK;
    io_unlock(io);xSemaphoreGive(io->camera_control);return ESP_OK;
}
esp_err_t screen_camera_service_page(screen_io_handle_t io,bool enabled){return request(io,false,enabled);}
esp_err_t screen_camera_service_raw(screen_io_handle_t io,bool enabled){return request(io,true,enabled);}
bool screen_camera_service_live(screen_io_handle_t io)
{
    io_lock(io);bool live=io->render.enabled && io->cam.requested && io->camera_phase!=SCREEN_CAMERA_ERROR && io->render.error==ESP_OK && (!io->render.latest_us || esp_timer_get_time()-io->render.latest_us<=500000);io_unlock(io);return live;
}
