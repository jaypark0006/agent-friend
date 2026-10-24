#include "screen_logic.h"
#include <stdlib.h>
/* Pure shared logic: edge gestures outrank page navigation. */
screen_page_t screen_navigate(screen_page_t page, int x0, int y0, int x1, int y1)
{
    int dx=x1-x0, dy=y1-y0;
    if (!screen_is_main(page) && y0 >= SCREEN_SIZE-SCREEN_BOTTOM_GESTURE_ZONE && dy <= -SCREEN_VERTICAL_GESTURE_DISTANCE && abs(dy)>abs(dx)) return PAGE_STATUS;
    if (y0 <= SCREEN_TOP_GESTURE_ZONE && dy >= SCREEN_VERTICAL_GESTURE_DISTANCE && abs(dy)>abs(dx)) return PAGE_SETTINGS;
    if (abs(dx)<SCREEN_HORIZONTAL_GESTURE_DISTANCE || abs(dx)<=abs(dy)) return page;
    if (screen_is_main(page)) {
        const screen_page_t pages[]={PAGE_STATUS,PAGE_WIDGET,PAGE_HOME,PAGE_TEXT,PAGE_CAMERA};
        unsigned index=0;
        for(unsigned i=0;i<5;i++) { if(pages[i]==page){ index=i; break; } }
        return pages[(index+(dx<0?1:4))%5];
    }
    if (page>=PAGE_METRICS && page<=PAGE_API)
        return PAGE_METRICS + (page-PAGE_METRICS+(dx<0?1:2))%3;
    return page;
}
/* Validate baseline SOF and bounded marker lengths before handing to HW.
 * Entropy stream validity remains the decoder's responsibility. */
bool screen_jpeg_dimensions(const uint8_t *p, unsigned n)
{
    if (!p || n<4 || n>SCREEN_JPEG_MAX || p[0]!=0xff || p[1]!=0xd8) return false;
    unsigned i=2;
    while (i+3<n) {
        if (p[i++]!=0xff) return false;
        while (i<n && p[i]==0xff) i++;
        if (i>=n) return false;
        uint8_t m=p[i++];
        if (m==0xda || m==0xd9 || m==0x00) return false;
        if (m==0x01 || (m>=0xd0 && m<=0xd7)) continue;
        if (i+2>n) return false;
        unsigned len=((unsigned)p[i]<<8)|p[i+1];
        if (len<2 || len>n-i) return false;
        if (m>=0xc0 && m<=0xcf && m!=0xc4 && m!=0xc8 && m!=0xcc) {
            if (m!=0xc0 || len!=17 || p[i+2]!=8 || p[i+7]!=3) return false;
            unsigned h=((unsigned)p[i+3]<<8)|p[i+4], w=((unsigned)p[i+5]<<8)|p[i+6];
            return w==SCREEN_SIZE && h==SCREEN_SIZE;
        }
        i+=len;
    }
    return false;
}

screen_page_t screen_touch_update(screen_touch_state_t *s, screen_page_t page,
    bool valid, bool down, int x, int y, uint32_t now)
{
    s->history_delta=0;
    if(!valid) {
        if(s->down && (uint32_t)(now-s->last_sample_ms)>=SCREEN_TOUCH_TIMEOUT_MS) {
            s->down=false; s->consumed=false;
        }
        return page;
    }
    s->last_sample_ms=now;
    if(!down) { s->down=false; s->consumed=false; return page; }
    if(!s->down) { s->start_x=x; s->start_y=y; s->consumed=false; }
    s->down=true; s->x=x; s->y=y;
    if(s->consumed) return page;
    screen_page_t target=screen_navigate(page,s->start_x,s->start_y,x,y);
    if(target!=page) s->consumed=true;
    else if(page==PAGE_HOME && abs(y-s->start_y)>=SCREEN_HORIZONTAL_GESTURE_DISTANCE && abs(y-s->start_y)>abs(x-s->start_x)) {
        s->history_delta=y<s->start_y?1:-1; s->consumed=true;
    }
    return target;
}
