#include "screen_private.h"
#include "screen_renderer.h"
#include "screen_camera_service.h"
#include "esp_timer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Compact numerical history overlay; keep photos at full 480x480. */
static void image_caption(struct screen_app *a,uint8_t *pixels)
{
    static const uint16_t digits[]={0x7b6f,0x2492,0x73e7,0x73cf,0x5bc9,0x79cf,0x79ef,0x7249,0x7bef,0x7bcf};
    char caption[24]="--:--"; screen_lock(a);
    int i=screen_history_find(&a->images,a->image_display_id);
    if(i>=0) {
        unsigned pos=0; while(pos<a->images.count && screen_history_at(&a->images,pos)!=i) pos++;
        snprintf(caption,sizeof(caption),"%s  %u/%u",a->images.entries[i].time,pos+1,a->images.count);
    } else snprintf(caption,sizeof(caption),"--:--  %u",a->images.count);
    screen_unlock(a);
    unsigned len=strlen(caption);
    for(int y=14;y<40;y++) for(unsigned x=14;x<22+len*8;x++) {
        size_t at=(y*480+x)*2; pixels[at]=0x10; pixels[at+1]=0x83;
    }
    for(unsigned n=0;n<len;n++) {
        char c=caption[n]; uint16_t bits=c>='0' && c<='9'?digits[c-'0']:c==':'?0x0410:c=='/'?0x12a4:c=='-'?0x01c0:0;
        for(unsigned y=0;y<5;y++) for(unsigned x=0;x<3;x++) if(bits&(1u<<(14-y*3-x))) {
            for(unsigned sy=0;sy<2;sy++) for(unsigned sx=0;sx<2;sx++) {
                size_t at=((22+y*2+sy)*480+20+n*8+x*2+sx)*2; pixels[at]=0xf7; pixels[at+1]=0xbe;
            }
        }
    }
}
void screen_renderer_badge(struct screen_app *a,uint8_t *pixels)
{
    screen_lock(a); bool show=a->overlay_enabled; screen_unlock(a);
    if(!show) return;
    if(a->image_display_id) image_caption(a,pixels);
    bool read=false; screen_lock(a);
    int i=screen_history_find(&a->images,a->image_display_id);
    if(i>=0) read=a->images.entries[i].read;
    screen_unlock(a);
    if(i>=0) for(int y=14;y<50;y++) for(int x=430;x<466;x++) {
        int dx=x-448,dy=y-32; if(dx*dx+dy*dy>17*17) continue;
        bool mark=read?((x>=438 && x<=445 && abs(y-(32+x-438))<=2) || (x>=445 && x<=458 && abs(y-(39-(x-445)))<=2)):(dx*dx+dy*dy<=8*8);
        uint16_t color=mark?(read?0x7c51:0x3f33):0x1083;
        size_t at=(y*480+x)*2; pixels[at]=color>>8; pixels[at+1]=color;
    }
    /* A stable footprint lets an unread update replace the old overlay
     * without accumulating old pixels or decoding the photo again. */
    screen_lock(a); unsigned unread=screen_history_unread(&a->messages); screen_unlock(a);
    a->image_notice_unread=unread;
    uint16_t ink=unread?0x3f33:0x7c51;
    for(int y=438;y<470;y++) for(int x=380;x<466;x++) {
        size_t at=(y*480+x)*2; pixels[at]=0x10; pixels[at+1]=0x83;
        bool envelope=(x>=389 && x<=411 && (y==447 || y==460)) ||
            (y>=447 && y<=460 && (x==389 || x==411)) ||
            (x>=389 && x<=400 && y==447+(x-389)/2) ||
            (x>=400 && x<=411 && y==447+(411-x)/2);
        if(envelope) { pixels[at]=ink>>8; pixels[at+1]=ink; }
    }
    static const uint16_t digits[]={0x7b6f,0x2492,0x73e7,0x73cf,0x5bc9,0x79cf,0x79ef,0x7249,0x7bef,0x7bcf};
    char count[12]; snprintf(count,sizeof(count),"%u",unread);
    for(unsigned n=0;count[n];n++) for(unsigned y=0;y<5;y++) for(unsigned x=0;x<3;x++)
        if(digits[count[n]-'0']&(1u<<(14-y*3-x))) for(unsigned dy=0;dy<3;dy++) for(unsigned dx=0;dx<3;dx++) {
            size_t at=((447+y*3+dy)*480+421+n*12+x*3+dx)*2;
            pixels[at]=ink>>8; pixels[at+1]=ink;
        }
}
bool screen_renderer_prepare(screen_app_handle_t a,screen_rendered_frame_t *frame)
{
    int64_t now=esp_timer_get_time();
        screen_lock(a);
        bool follow=a->images.follow_latest;
        uint32_t selected=a->images.selected_id;
        screen_unlock(a);
        bool camera_live=a->page==PAGE_CAMERA && screen_camera_service_live(a->io);
        int slot=a->page==PAGE_HOME && follow && !camera_live?screen_frame_take(a):-1;
        int64_t camera_received_us=now;
        bool camera_frame=camera_live && screen_camera_render_take(a->io,a->pixels[a->output_index],&camera_received_us,screen_camera_frame_rotation(a->display_rotation_cw_deg));
        screen_image_blob_t *image=NULL;size_t size=0;const uint8_t *jpeg=NULL; uint32_t history_id=0; int64_t received_us=now;
        if(slot>=0) {
            struct frame_slot *f=&a->frames[slot];
            jpeg=f->data; size=f->len; received_us=f->received_us; history_id=f->history_id;
        } else if(!camera_live && a->page==PAGE_HOME && selected && selected!=a->rendered_image_id) {
            image=screen_image_acquire(a,selected);
            if(image){size=screen_image_size(image);jpeg=screen_image_data(image);history_id=selected;}
        }
        if(jpeg || camera_frame) {
            unsigned idx=a->output_index;
            /* Decode into the spare buffer while the previous front buffer is
             * being transmitted. Drain before drawing or recycling the front. */
            jpeg_decode_cfg_t cfg={.output_format=JPEG_DECODE_OUT_FORMAT_RGB565,.rgb_order=JPEG_DEC_RGB_ELEMENT_ORDER_RGB,.conv_std=JPEG_YUV_RGB_CONV_STD_BT601};
            uint32_t written=0; int64_t t=esp_timer_get_time();
            esp_err_t e=ESP_OK;
            if(camera_frame){written=480*480*2;received_us=camera_received_us;history_id=0;}
            else e=jpeg_decoder_process(a->decoder,&cfg,jpeg,size,a->pixels[idx],a->pixel_capacity[idx],&written);
            screen_lock(a); if(!camera_frame) a->decode_ms=(esp_timer_get_time()-t)/1000.0f; if(e!=ESP_OK || written!=480*480*2) a->invalid++; screen_unlock(a);
            if(slot>=0) screen_frame_release(a,slot);
            screen_image_release(a,image);
            if(e==ESP_OK && written==480*480*2) {
                *frame=(screen_rendered_frame_t){.camera=camera_frame,.counts_frame=slot>=0,.history_id=history_id,.selected_id=selected,.received_us=received_us};
                return true;
            }
        }
        return false;
}
