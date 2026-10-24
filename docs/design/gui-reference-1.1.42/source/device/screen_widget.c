#include "screen_private.h"
#include "screen_widget.h"
#include "screen_http.h"
#include "screen_font.h"
#include "esp_timer.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static struct screen_app *s_widget_app = NULL;

static void utf8_safe_copy(char *dst, const char *src, size_t dst_size)
{
    if(!dst || dst_size == 0) return;
    if(!src) { dst[0] = '\0'; return; }
    size_t src_len = strlen(src);
    if(src_len < dst_size) {
        memcpy(dst, src, src_len + 1);
        return;
    }
    size_t copy_len = dst_size - 1;
    memcpy(dst, src, copy_len);
    dst[copy_len] = '\0';

    size_t i = copy_len;
    while(i > 0 && ((unsigned char)dst[i - 1] & 0xC0) == 0x80) {
        i--;
    }
    if(i > 0) {
        unsigned char lead = (unsigned char)dst[i - 1];
        size_t needed = 0;
        if((lead & 0x80) == 0) needed = 1;
        else if((lead & 0xE0) == 0xC0) needed = 2;
        else if((lead & 0xF0) == 0xE0) needed = 3;
        else if((lead & 0xF8) == 0xF0) needed = 4;

        if(copy_len - (i - 1) < needed) {
            dst[i - 1] = '\0';
        }
    }
}

static uint32_t parse_color(const char *s, uint32_t default_color)
{
    if(!s || !*s) return default_color;
    if(*s=='#') s++;
    char *end=NULL;
    unsigned long val=strtoul(s,&end,16);
    return (end && *end=='\0') ? (uint32_t)val : default_color;
}

static void recompute_counts(struct screen_widget_state *w)
{
    uint32_t act=0, don=0;
    for(uint32_t i=0;i<w->count;i++) {
        if(w->items[i].active) {
            if(w->items[i].done) don++;
            else act++;
        }
    }
    w->active_count=act;
    w->done_count=don;
}

void screen_widget_init(struct screen_app *a)
{
    s_widget_app=a;
    struct screen_widget_state *w=&a->widget;
    memset(w,0,sizeof(*w));
    w->count=0;
    w->active_count=0;
    w->done_count=0;
    w->generation=1;
    w->update_us=esp_timer_get_time();
    a->widget_scroll_y=0;
    a->widget_scroll_max=0;
    a->widget_scroll_saved=false;
}

static void update_one_agent(struct screen_widget_state *w, const cJSON *j)
{
    if(!j || !cJSON_IsObject(j)) return;
    const cJSON *id_item=cJSON_GetObjectItemCaseSensitive(j,"id");
    const char *id=(cJSON_IsString(id_item) && id_item->valuestring && *id_item->valuestring)?id_item->valuestring:"assistant";

    const cJSON *del=cJSON_GetObjectItemCaseSensitive(j,"delete");
    if(cJSON_IsTrue(del)) {
        for(uint32_t i=0;i<w->count;i++) {
            if(w->items[i].active && !strcmp(w->items[i].id,id)) {
                for(uint32_t k=i;k+1<w->count;k++) w->items[k]=w->items[k+1];
                w->count--;
                memset(&w->items[w->count],0,sizeof(w->items[w->count]));
                break;
            }
        }
        recompute_counts(w);
        return;
    }

    const cJSON *title=cJSON_GetObjectItemCaseSensitive(j,"title");
    const cJSON *status=cJSON_GetObjectItemCaseSensitive(j,"status");
    const cJSON *badge=cJSON_GetObjectItemCaseSensitive(j,"badge");
    const cJSON *progress=cJSON_GetObjectItemCaseSensitive(j,"progress");
    const cJSON *color=cJSON_GetObjectItemCaseSensitive(j,"color");
    const cJSON *done=cJSON_GetObjectItemCaseSensitive(j,"done");

    int target_idx=-1;
    /* Direct Task Key match: the Agent decides its unique task ID */
    for(uint32_t i=0; i<w->count; i++) {
        if(w->items[i].active && !strcmp(w->items[i].id, id)) {
            target_idx=(int)i;
            break;
        }
    }

    if(target_idx<0) {
        /* New task arriving: append at bottom of queue */
        if(w->count>=SCREEN_WIDGET_MAX_QUEUE) {
            /* Evict oldest item from the top */
            for(uint32_t k=0;k+1<SCREEN_WIDGET_MAX_QUEUE;k++) w->items[k]=w->items[k+1];
            w->count=SCREEN_WIDGET_MAX_QUEUE-1;
            memset(&w->items[w->count],0,sizeof(w->items[w->count]));
        }
        target_idx=(int)w->count;
        w->count++;
        w->items[target_idx].active=true;
        w->items[target_idx].created_us=esp_timer_get_time();
        strlcpy(w->items[target_idx].id,id,sizeof(w->items[target_idx].id));
    }

    struct screen_agent_item *it=&w->items[target_idx];
    if(cJSON_IsString(title) && title->valuestring && *title->valuestring) utf8_safe_copy(it->title,title->valuestring,sizeof(it->title));
    else if(!it->title[0]) utf8_safe_copy(it->title,"Task",sizeof(it->title));
    if(cJSON_IsString(status) && status->valuestring) utf8_safe_copy(it->status,status->valuestring,sizeof(it->status));
    if(cJSON_IsString(badge) && badge->valuestring) utf8_safe_copy(it->badge,badge->valuestring,sizeof(it->badge));
    if(cJSON_IsNumber(progress)) {
        it->progress=progress->valueint;
        if(it->progress>=100) it->done=true;
        else if(!cJSON_IsBool(done)) it->done=false;
    }
    if(cJSON_IsString(color) && color->valuestring) it->color_hex=parse_color(color->valuestring,it->color_hex?it->color_hex:0x39e69d);
    else if(!it->color_hex) it->color_hex=0x39e69d;
    if(cJSON_IsBool(done)) it->done=cJSON_IsTrue(done);

    const cJSON *action=cJSON_GetObjectItemCaseSensitive(j,"action");
    if(cJSON_IsObject(action)) {
        const cJSON *act_type=cJSON_GetObjectItemCaseSensitive(action,"type");
        if(cJSON_IsString(act_type) && act_type->valuestring) strlcpy(it->action_type,act_type->valuestring,sizeof(it->action_type));
        else strlcpy(it->action_type,"confirm",sizeof(it->action_type));
        const cJSON *opts=cJSON_GetObjectItemCaseSensitive(action,"options");
        if(cJSON_IsArray(opts) && cJSON_GetArraySize(opts)>=2) {
            const cJSON *o1=cJSON_GetArrayItem(opts,0);
            const cJSON *o2=cJSON_GetArrayItem(opts,1);
            if(cJSON_IsString(o1) && o1->valuestring) strlcpy(it->action_btn1,o1->valuestring,sizeof(it->action_btn1));
            if(cJSON_IsString(o2) && o2->valuestring) strlcpy(it->action_btn2,o2->valuestring,sizeof(it->action_btn2));
        } else {
            strlcpy(it->action_btn1,"Approve",sizeof(it->action_btn1));
            strlcpy(it->action_btn2,"Cancel",sizeof(it->action_btn2));
        }
        it->action_result[0]='\0';
    } else if(cJSON_IsString(action) && action->valuestring) {
        strlcpy(it->action_type,action->valuestring,sizeof(it->action_type));
        strlcpy(it->action_btn1,"Approve",sizeof(it->action_btn1));
        strlcpy(it->action_btn2,"Cancel",sizeof(it->action_btn2));
        it->action_result[0]='\0';
    }

    it->update_us=esp_timer_get_time();
    recompute_counts(w);
}

esp_err_t screen_widget_update(struct screen_app *a, const cJSON *j, bool *switch_to_widget)
{
    if(!j || !cJSON_IsObject(j)) return ESP_ERR_INVALID_ARG;

    screen_lock(a);
    struct screen_widget_state *w=&a->widget;

    const cJSON *clear_all=cJSON_GetObjectItemCaseSensitive(j,"clear_all");
    if(cJSON_IsTrue(clear_all)) {
        memset(w->items,0,sizeof(w->items));
        w->count=0;
        w->active_count=0;
        w->done_count=0;
    }

    const cJSON *agents=cJSON_GetObjectItemCaseSensitive(j,"agents");
    if(cJSON_IsArray(agents)) {
        int sz=cJSON_GetArraySize(agents);
        for(int i=0;i<sz;i++) update_one_agent(w,cJSON_GetArrayItem(agents,i));
    } else {
        update_one_agent(w,j);
    }

    w->generation++;
    w->update_us=esp_timer_get_time();
    screen_unlock(a);

    if(a->interact) {
        /* Transient notification indicator only — never stay permanently illuminated */
        bool has_new_confirm = false;
        bool has_just_done = false;
        int64_t now = esp_timer_get_time();
        for(uint32_t i=0;i<w->count;i++) {
            if(w->items[i].active) {
                if(w->items[i].action_type[0]=='c' && w->items[i].action_result[0]=='\0') has_new_confirm=true;
                if(w->items[i].done && (now - w->items[i].update_us < 2000000LL)) has_just_done=true;
            }
        }
        if(has_new_confirm) {
            screen_interact_set_leds_rgb(a->interact, 1, 240, 140, 0, 12);
            a->interact_leds_off_us = now + 1500000LL;
        } else if(has_just_done) {
            screen_interact_set_leds_rgb(a->interact, 1, 40, 220, 80, 12);
            a->interact_leds_off_us = now + 1500000LL;
        } else {
            screen_interact_set_leds_rgb(a->interact, 1, 0, 0, 0, 0);
            a->interact_leds_off_us = 0;
        }
    }

    const cJSON *show=cJSON_GetObjectItemCaseSensitive(j,"show");
    bool do_switch=!show || cJSON_IsTrue(show);
    if(switch_to_widget) *switch_to_widget=do_switch;
    return ESP_OK;
}

cJSON *screen_widget_json(struct screen_app *a)
{
    cJSON *j=cJSON_CreateObject();
    if(!j) return NULL;
    screen_lock(a);
    const struct screen_widget_state *w=&a->widget;

    cJSON_AddNumberToObject(j,"count",w->count);
    cJSON_AddNumberToObject(j,"active_count",w->active_count);
    cJSON_AddNumberToObject(j,"done_count",w->done_count);
    cJSON_AddNumberToObject(j,"generation",w->generation);
    cJSON_AddNumberToObject(j,"update_us",w->update_us);

    cJSON *arr=cJSON_AddArrayToObject(j,"agents");
    for(uint32_t i=0;i<w->count;i++) {
        if(!w->items[i].active) continue;
        cJSON *it=cJSON_CreateObject();
        cJSON_AddStringToObject(it,"id",w->items[i].id);
        cJSON_AddStringToObject(it,"title",w->items[i].title);
        cJSON_AddStringToObject(it,"status",w->items[i].status);
        cJSON_AddStringToObject(it,"badge",w->items[i].badge);
        cJSON_AddNumberToObject(it,"progress",w->items[i].progress);
        char col[10]; snprintf(col,sizeof(col),"#%06lx",(unsigned long)(w->items[i].color_hex & 0xffffff));
        cJSON_AddStringToObject(it,"color",col);
        cJSON_AddBoolToObject(it,"done",w->items[i].done);
        cJSON_AddNumberToObject(it,"created_us",w->items[i].created_us);
        cJSON_AddNumberToObject(it,"update_us",w->items[i].update_us);
        if(w->items[i].action_type[0]) {
            cJSON *act=cJSON_AddObjectToObject(it,"action");
            cJSON_AddStringToObject(act,"type",w->items[i].action_type);
            cJSON_AddStringToObject(act,"btn1",w->items[i].action_btn1);
            cJSON_AddStringToObject(act,"btn2",w->items[i].action_btn2);
            cJSON_AddStringToObject(act,"result",w->items[i].action_result);
        }
        cJSON_AddItemToArray(arr,it);
    }
    screen_unlock(a);
    return j;
}

esp_err_t screen_http_widget(httpd_req_t *r)
{
    struct screen_app *a=r->user_ctx;
    screen_activity_kick(a);
    if(r->method==HTTP_POST) {
        cJSON *j=NULL;
        if(screen_http_read_json(r,a->rx,SCREEN_JPEG_MAX,2048,"Expected JSON <=2048 bytes",true,&j)!=ESP_OK) return ESP_FAIL;
        bool switch_page=false;
        esp_err_t err=screen_widget_update(a,j,&switch_page);
        cJSON_Delete(j);
        if(err!=ESP_OK) return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid widget payload");
        if(switch_page) {
            screen_lock(a);
            screen_pages_request_locked(a,PAGE_WIDGET);
            screen_unlock(a);
        }
    }
    cJSON *resp=screen_widget_json(a);
    if(!resp) return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"No memory");
    return screen_http_send_json(r,resp);
}

static void anim_opa_cb(void *obj, int32_t val)
{
    if(s_widget_app && (s_widget_app->touch_state.down || (s_widget_app->widget_list_box && lv_obj_is_scrolling(s_widget_app->widget_list_box)))) {
        return;
    }
    lv_obj_set_style_opa((lv_obj_t *)obj, (lv_opa_t)val, 0);
}

static void anim_x_cb(void *obj, int32_t x)
{
    if(!s_widget_app) return;
    bool moving = s_widget_app->touch_state.down || 
                  (s_widget_app->widget_list_box && lv_obj_is_scrolling(s_widget_app->widget_list_box));
    if(moving) {
        if(!lv_obj_has_flag((lv_obj_t *)obj, LV_OBJ_FLAG_HIDDEN)) {
            lv_obj_add_flag((lv_obj_t *)obj, LV_OBJ_FLAG_HIDDEN);
        }
        return;
    } else {
        if(lv_obj_has_flag((lv_obj_t *)obj, LV_OBJ_FLAG_HIDDEN)) {
            lv_obj_remove_flag((lv_obj_t *)obj, LV_OBJ_FLAG_HIDDEN);
        }
    }
    lv_obj_set_x((lv_obj_t *)obj, x);
}

static lv_grad_dsc_t s_beam_grad_left;
static lv_grad_dsc_t s_beam_grad_right;
static bool s_beam_grad_inited = false;

static void ensure_beam_grad_inited(void)
{
    if(s_beam_grad_inited) return;
    memset(&s_beam_grad_left, 0, sizeof(s_beam_grad_left));
    s_beam_grad_left.stops_count = 2;
    s_beam_grad_left.dir = LV_GRAD_DIR_HOR;
    s_beam_grad_left.stops[0].color = lv_color_hex(0xffffff);
    s_beam_grad_left.stops[0].opa = LV_OPA_0;
    s_beam_grad_left.stops[0].frac = 0;
    s_beam_grad_left.stops[1].color = lv_color_hex(0xffffff);
    s_beam_grad_left.stops[1].opa = LV_OPA_90;
    s_beam_grad_left.stops[1].frac = 255;

    memset(&s_beam_grad_right, 0, sizeof(s_beam_grad_right));
    s_beam_grad_right.stops_count = 2;
    s_beam_grad_right.dir = LV_GRAD_DIR_HOR;
    s_beam_grad_right.stops[0].color = lv_color_hex(0xffffff);
    s_beam_grad_right.stops[0].opa = LV_OPA_90;
    s_beam_grad_right.stops[0].frac = 0;
    s_beam_grad_right.stops[1].color = lv_color_hex(0xffffff);
    s_beam_grad_right.stops[1].opa = LV_OPA_0;
    s_beam_grad_right.stops[1].frac = 255;

    s_beam_grad_inited = true;
}

bool screen_widget_trigger_action(struct screen_app *a, int which)
{
    if(!a) return false;
    bool handled=false;
    screen_lock(a);
    struct screen_widget_state *w=&a->widget;
    for(uint32_t i=0;i<w->count;i++) {
        if(w->items[i].active && w->items[i].action_type[0]=='c' && w->items[i].action_result[0]=='\0') {
            struct screen_agent_item *it=&w->items[i];
            const char *choice=(which==1)?it->action_btn1:it->action_btn2;
            strlcpy(it->action_result,choice,sizeof(it->action_result));
            it->done=true;
            it->progress=(which==1)?100:0;
            char new_status[SCREEN_WIDGET_STATUS_MAX+1];
            snprintf(new_status,sizeof(new_status),"%s: %s",(which==1)?"Confirmed":"Cancelled",choice);
            strlcpy(it->status,new_status,sizeof(it->status));
            it->update_us=esp_timer_get_time();
            w->generation++;
            w->update_us=esp_timer_get_time();
            handled=true;
            break;
        }
    }
    screen_unlock(a);
    if(handled) {
        screen_activity_kick(a);
        if(a->interact) {
            if(which==1) screen_interact_set_leds_rgb(a->interact,0,0x39,0xe6,0x9d,50);
            else screen_interact_set_leds_rgb(a->interact,0,0xe5,0xc0,0x7b,40);
            a->interact_leds_off_us=esp_timer_get_time()+1500000;
        }
        screen_ui_widget_refresh(a);
    }
    return handled;
}

static void action_btn_cb(lv_event_t *e)
{
    struct screen_app *a=lv_event_get_user_data(e);
    lv_obj_t *btn=lv_event_get_target_obj(e);
    uintptr_t which=(uintptr_t)lv_obj_get_user_data(btn);
    screen_widget_trigger_action(a,(int)which);
}

static void update_agent_card(struct screen_app *a, lv_obj_t *card, const struct screen_agent_item *it, uint32_t idx, const lv_font_t *font)
{
    bool has_action=(it->action_type[0]=='c' && it->action_result[0]=='\0');
    lv_obj_set_size(card,444,has_action?116:84);
    lv_obj_set_user_data(card,(void*)(uintptr_t)idx);
    if(it->done) {
        lv_obj_set_style_bg_color(card,lv_color_hex(0x131a24),0);
    } else {
        lv_obj_set_style_bg_color(card,lv_color_hex(0x182433),0);
    }
    lv_obj_set_style_border_width(card,0,0);

    lv_obj_t *dot=lv_obj_get_child(card,0);
    if(dot) {
        lv_obj_set_style_bg_color(dot,lv_color_hex(it->done?0x39e69d:it->color_hex),0);
        if(it->done) {
            lv_anim_delete(dot,anim_opa_cb);
            lv_obj_set_style_opa(dot,LV_OPA_COVER,0);
        } else {
            lv_anim_delete(dot,anim_opa_cb);
            lv_anim_t da; lv_anim_init(&da);
            lv_anim_set_var(&da,dot);
            lv_anim_set_exec_cb(&da,anim_opa_cb);
            lv_anim_set_values(&da,LV_OPA_30,LV_OPA_COVER);
            lv_anim_set_duration(&da,700);
            lv_anim_set_playback_duration(&da,700);
            lv_anim_set_repeat_count(&da,LV_ANIM_REPEAT_INFINITE);
            lv_anim_set_path_cb(&da,lv_anim_path_ease_in_out);
            lv_anim_start(&da);
        }
    }

    lv_obj_t *title=lv_obj_get_child(card,1);
    if(title) {
        lv_label_set_text(title,it->title);
        lv_obj_set_style_text_color(title,lv_color_hex(it->done?0xd0dce8:0xf0f4fa),0);
    }

    lv_obj_t *pct_label=lv_obj_get_child(card,2);
    if(pct_label) {
        if(it->done || it->progress>=100) {
            lv_label_set_text(pct_label,"DONE");
            lv_obj_set_style_text_color(pct_label,lv_color_hex(0x39e69d),0);
        } else if(it->progress>=0) {
            char buf[16]; snprintf(buf,sizeof(buf),"%d%%",it->progress);
            lv_label_set_text(pct_label,buf);
            lv_obj_set_style_text_color(pct_label,lv_color_hex(0x8ec5fc),0);
        } else {
            lv_label_set_text(pct_label,it->badge[0]?it->badge:"ACTIVE");
            lv_obj_set_style_text_color(pct_label,lv_color_hex(it->color_hex),0);
        }
    }

    lv_obj_t *bar=lv_obj_get_child(card,3);
    if(bar) {
        if(it->progress>=0 || it->done) {
            lv_obj_remove_flag(bar,LV_OBJ_FLAG_HIDDEN);
            lv_bar_set_value(bar,it->done?100:(it->progress>=0?it->progress:0),LV_ANIM_OFF);
            lv_obj_set_style_bg_color(bar,lv_color_hex(it->done?0x2d6b4f:it->color_hex),LV_PART_INDICATOR);
            lv_obj_t *shimmer=lv_obj_get_child(bar,0);
            if(shimmer) {
                if(it->done) {
                    lv_anim_delete(shimmer,anim_x_cb);
                    lv_obj_add_flag(shimmer,LV_OBJ_FLAG_HIDDEN);
                } else {
                    lv_obj_remove_flag(shimmer,LV_OBJ_FLAG_HIDDEN);
                    lv_anim_delete(shimmer,anim_x_cb);
                    lv_anim_t sa; lv_anim_init(&sa);
                    lv_anim_set_var(&sa,shimmer);
                    lv_anim_set_exec_cb(&sa,anim_x_cb);
                    lv_anim_set_values(&sa,-90,420);
                    lv_anim_set_duration(&sa,1500);
                    lv_anim_set_repeat_count(&sa,LV_ANIM_REPEAT_INFINITE);
                    lv_anim_set_repeat_delay(&sa,250);
                    lv_anim_set_path_cb(&sa,lv_anim_path_ease_in_out);
                    lv_anim_start(&sa);
                }
            }
        } else {
            lv_obj_add_flag(bar,LV_OBJ_FLAG_HIDDEN);
        }
    }

    lv_obj_t *status=lv_obj_get_child(card,4);
    if(status) {
        lv_label_set_text(status,it->status);
        lv_obj_set_style_text_color(status,lv_color_hex(it->done?0x758899:0x9fb1c5),0);
    }

    lv_obj_t *btn1=lv_obj_get_child(card,5);
    lv_obj_t *btn2=lv_obj_get_child(card,6);
    if(btn1 && btn2) {
        if(has_action) {
            lv_obj_remove_flag(btn1,LV_OBJ_FLAG_HIDDEN);
            lv_obj_remove_flag(btn2,LV_OBJ_FLAG_HIDDEN);
            lv_obj_t *l1=lv_obj_get_child(btn1,0);
            if(l1) {
                char buf[36];
                snprintf(buf,sizeof(buf),"[L] %s",it->action_btn1[0]?it->action_btn1:"Approve");
                lv_label_set_text(l1,buf);
            }
            lv_obj_t *l2=lv_obj_get_child(btn2,0);
            if(l2) {
                char buf[36];
                snprintf(buf,sizeof(buf),"[R] %s",it->action_btn2[0]?it->action_btn2:"Cancel");
                lv_label_set_text(l2,buf);
            }
        } else {
            lv_obj_add_flag(btn1,LV_OBJ_FLAG_HIDDEN);
            lv_obj_add_flag(btn2,LV_OBJ_FLAG_HIDDEN);
        }
    }
}

static lv_obj_t *build_agent_card(struct screen_app *a, lv_obj_t *parent, const struct screen_agent_item *it, uint32_t idx, const lv_font_t *font)
{
    lv_obj_t *card=lv_obj_create(parent);
    lv_obj_set_size(card,444,84);
    lv_obj_set_style_bg_opa(card,LV_OPA_COVER,0);
    lv_obj_set_style_border_width(card,0,0);
    lv_obj_set_style_radius(card,8,0);
    lv_obj_set_style_pad_all(card,0,0);
    lv_obj_remove_flag(card,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(card,LV_OBJ_FLAG_CLICKABLE);

    /* Child 0: dot */
    lv_obj_t *dot=lv_obj_create(card);
    lv_obj_set_pos(dot,12,11); lv_obj_set_size(dot,10,10);
    lv_obj_set_style_radius(dot,LV_RADIUS_CIRCLE,0);
    lv_obj_set_style_border_width(dot,0,0);
    lv_obj_remove_flag(dot,LV_OBJ_FLAG_CLICKABLE);

    /* Child 1: title */
    lv_obj_t *title=lv_label_create(card);
    lv_obj_set_pos(title,28,6); lv_obj_set_width(title,280);
    lv_obj_set_style_text_font(title,font,0);

    /* Child 2: pct_label */
    lv_obj_t *pct_label=lv_label_create(card);
    lv_obj_set_pos(pct_label,320,6); lv_obj_set_width(pct_label,112);
    lv_obj_set_style_text_align(pct_label,LV_TEXT_ALIGN_RIGHT,0);
    lv_obj_set_style_text_font(pct_label,&lv_font_montserrat_14,0);

    /* Child 3: bar */
    lv_obj_t *bar=lv_bar_create(card);
    lv_obj_set_pos(bar,12,32); lv_obj_set_size(bar,420,10);
    lv_bar_set_range(bar,0,100);
    lv_obj_set_style_bg_color(bar,lv_color_hex(0x1c2836),LV_PART_MAIN);
    lv_obj_set_style_bg_opa(bar,LV_OPA_COVER,LV_PART_MAIN);
    lv_obj_set_style_radius(bar,3,LV_PART_MAIN);
    lv_obj_set_style_bg_opa(bar,LV_OPA_COVER,LV_PART_INDICATOR);
    lv_obj_set_style_radius(bar,3,LV_PART_INDICATOR);
    lv_obj_remove_flag(bar,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(bar,LV_OBJ_FLAG_CLICKABLE);

    /* Shimmer inside bar: symmetric dual-gradient beam (shallow on both sides, deep in center) */
    ensure_beam_grad_inited();
    lv_obj_t *shimmer=lv_obj_create(bar);
    lv_obj_remove_flag(shimmer,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(shimmer,LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(shimmer,90,10); lv_obj_set_pos(shimmer,-90,0);
    lv_obj_set_style_radius(shimmer,0,0);
    lv_obj_set_style_border_width(shimmer,0,0);
    lv_obj_set_style_bg_opa(shimmer,LV_OPA_TRANSP,0);
    lv_obj_set_style_pad_all(shimmer,0,0);

    /* Left half of shimmer: 0% -> 90% opacity white */
    lv_obj_t *shimmer_l=lv_obj_create(shimmer);
    lv_obj_remove_flag(shimmer_l,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(shimmer_l,LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(shimmer_l,45,10); lv_obj_set_pos(shimmer_l,0,0);
    lv_obj_set_style_radius(shimmer_l,0,0);
    lv_obj_set_style_border_width(shimmer_l,0,0);
    lv_obj_set_style_pad_all(shimmer_l,0,0);
    lv_obj_set_style_bg_opa(shimmer_l,LV_OPA_COVER,0);
    lv_obj_set_style_bg_grad(shimmer_l,&s_beam_grad_left,0);

    /* Right half of shimmer: 90% -> 0% opacity white */
    lv_obj_t *shimmer_r=lv_obj_create(shimmer);
    lv_obj_remove_flag(shimmer_r,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(shimmer_r,LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(shimmer_r,45,10); lv_obj_set_pos(shimmer_r,45,0);
    lv_obj_set_style_radius(shimmer_r,0,0);
    lv_obj_set_style_border_width(shimmer_r,0,0);
    lv_obj_set_style_pad_all(shimmer_r,0,0);
    lv_obj_set_style_bg_opa(shimmer_r,LV_OPA_COVER,0);
    lv_obj_set_style_bg_grad(shimmer_r,&s_beam_grad_right,0);

    /* Child 4: status */
    lv_obj_t *status=lv_label_create(card);
    lv_obj_set_pos(status,12,48); lv_obj_set_width(status,420);
    lv_obj_set_style_text_font(status,font,0);

    /* Child 5: btn1 */
    lv_obj_t *btn1=lv_button_create(card);
    lv_obj_set_pos(btn1,12,72); lv_obj_set_size(btn1,200,34);
    lv_obj_set_style_bg_color(btn1,lv_color_hex(0x1a3828),0);
    lv_obj_set_style_border_color(btn1,lv_color_hex(0x39e69d),0);
    lv_obj_set_style_border_width(btn1,1,0);
    lv_obj_set_style_radius(btn1,6,0);
    lv_obj_set_user_data(btn1,(void*)(uintptr_t)1);
    lv_obj_add_event_cb(btn1,action_btn_cb,LV_EVENT_CLICKED,a);
    lv_obj_t *l1=lv_label_create(btn1);
    lv_obj_center(l1);
    lv_obj_set_style_text_color(l1,lv_color_hex(0x39e69d),0);
    lv_obj_set_style_text_font(l1,font,0);

    /* Child 6: btn2 */
    lv_obj_t *btn2=lv_button_create(card);
    lv_obj_set_pos(btn2,224,72); lv_obj_set_size(btn2,208,34);
    lv_obj_set_style_bg_color(btn2,lv_color_hex(0x232c37),0);
    lv_obj_set_style_border_color(btn2,lv_color_hex(0x4a5a6c),0);
    lv_obj_set_style_border_width(btn2,1,0);
    lv_obj_set_style_radius(btn2,6,0);
    lv_obj_set_user_data(btn2,(void*)(uintptr_t)2);
    lv_obj_add_event_cb(btn2,action_btn_cb,LV_EVENT_CLICKED,a);
    lv_obj_t *l2=lv_label_create(btn2);
    lv_obj_center(l2);
    lv_obj_set_style_text_color(l2,lv_color_hex(0xa0b0c0),0);
    lv_obj_set_style_text_font(l2,font,0);

    update_agent_card(a,card,it,idx,font);
    return card;
}

static int32_t get_card_height(lv_obj_t *card)
{
    if(!card) return 84;
    int32_t h = lv_obj_get_style_height(card, LV_PART_MAIN);
    if(h > 0) return h;
    lv_obj_update_layout(card);
    h = lv_obj_get_height(card);
    return (h > 0) ? h : 84;
}

static void widget_list_layout(struct screen_app *a)
{
    if(!a || !a->widget_list_box) return;
    int32_t y = 0;
    uint32_t cnt = lv_obj_get_child_count(a->widget_list_box);
    for(uint32_t i = 0; i < cnt; i++) {
        lv_obj_t *card = lv_obj_get_child(a->widget_list_box, i);
        if(!card) continue;
        int32_t h = get_card_height(card);
        lv_obj_set_pos(card, 2, y);
        y += h + 8;
    }
}

void screen_ui_widget_build(struct screen_app *a, lv_obj_t *root)
{
    s_widget_app = a;
    screen_lock(a);
    const struct screen_widget_state *w=&a->widget;
    const lv_font_t *font = (a && a->message_fonts) ? screen_font_get(a->message_fonts, 16) : &a->ui_font;
    if(!font) font = &a->ui_font;

    /* Header Dot */
    lv_obj_t *dot=lv_obj_create(root);
    lv_obj_set_pos(dot,24,24);
    lv_obj_set_size(dot,14,14);
    lv_obj_set_style_radius(dot,LV_RADIUS_CIRCLE,0);
    lv_obj_set_style_bg_color(dot,lv_color_hex(w->active_count>0?0x39e69d:0x607285),0);
    lv_obj_set_style_border_width(dot,0,0);

    if(w->active_count>0) {
        lv_anim_t hda;
        lv_anim_init(&hda);
        lv_anim_set_var(&hda,dot);
        lv_anim_set_exec_cb(&hda,anim_opa_cb);
        lv_anim_set_values(&hda,LV_OPA_40,LV_OPA_COVER);
        lv_anim_set_duration(&hda,900);
        lv_anim_set_playback_duration(&hda,900);
        lv_anim_set_repeat_count(&hda,LV_ANIM_REPEAT_INFINITE);
        lv_anim_set_path_cb(&hda,lv_anim_path_ease_in_out);
        lv_anim_start(&hda);
    }

    /* Header Title */
    a->widget_header_title=lv_label_create(root);
    char title_buf[64];
    if(w->done_count>0) snprintf(title_buf,sizeof(title_buf),"Pipeline (%lu Active • %lu Done)",(unsigned long)w->active_count,(unsigned long)w->done_count);
    else snprintf(title_buf,sizeof(title_buf),"Pipeline (%lu Active)",(unsigned long)w->active_count);
    lv_label_set_text(a->widget_header_title,title_buf);
    lv_obj_set_pos(a->widget_header_title,48,18);
    lv_obj_set_width(a->widget_header_title,248);
    lv_obj_set_style_text_font(a->widget_header_title,font,0);
    lv_obj_set_style_text_color(a->widget_header_title,lv_color_hex(0xf0f4fa),0);

    /* Page Indicator Dots (Page 1 = Pipeline) & Battery Indicator */
    screen_ui_draw_page_dots(a, root, 1, 5);

    /* Scrollable Agent Cards List (expanded height from 386 to 414) */
    a->widget_list_box=lv_obj_create(root);
    lv_obj_set_pos(a->widget_list_box,16,50);
    lv_obj_set_size(a->widget_list_box,448,414);
    lv_obj_set_style_bg_color(a->widget_list_box,lv_color_hex(0x101720),0);
    lv_obj_set_style_bg_opa(a->widget_list_box,LV_OPA_COVER,0);
    lv_obj_set_style_border_width(a->widget_list_box,0,0);
    lv_obj_set_style_pad_all(a->widget_list_box,0,0);
    lv_obj_set_scroll_dir(a->widget_list_box,LV_DIR_VER);
    lv_obj_set_scrollbar_mode(a->widget_list_box,LV_SCROLLBAR_MODE_AUTO);
    lv_obj_remove_flag(a->widget_list_box,LV_OBJ_FLAG_SCROLL_ELASTIC);
    lv_obj_add_flag(a->widget_list_box,LV_OBJ_FLAG_SCROLL_MOMENTUM);

    if(w->count==0) {
        lv_obj_t *empty=lv_label_create(a->widget_list_box);
        lv_label_set_text(empty,"No active agents in pipeline.\nPost progress via /api/widget.");
        lv_obj_set_style_text_font(empty,font,0);
        lv_obj_set_style_text_color(empty,lv_color_hex(0x607285),0);
        lv_obj_set_style_text_align(empty,LV_TEXT_ALIGN_CENTER,0);
        lv_obj_set_width(empty,420);
        lv_obj_set_style_pad_top(empty,60,0);
    } else {
        lv_obj_t *last_card=NULL;
        for(uint32_t i=0;i<w->count;i++) {
            if(w->items[i].active) last_card=build_agent_card(a,a->widget_list_box,&w->items[i],i,font);
        }
        widget_list_layout(a);
        lv_obj_update_layout(a->widget_list_box);
        if(a->widget_scroll_saved) {
            lv_obj_scroll_to_y(a->widget_list_box,a->widget_scroll_y,LV_ANIM_OFF);
        } else if(last_card) {
            lv_obj_scroll_to_view(last_card,LV_ANIM_OFF);
        }
    }

    /* Bottom Home Indicator Bar (Capsule) */
    lv_obj_t *home_bar=lv_obj_create(root);
    lv_obj_set_pos(home_bar,200,472);
    lv_obj_set_size(home_bar,80,4);
    lv_obj_set_style_bg_color(home_bar,lv_color_hex(0x2d3e52),0);
    lv_obj_set_style_bg_opa(home_bar,LV_OPA_COVER,0);
    lv_obj_set_style_radius(home_bar,2,0);
    lv_obj_set_style_border_width(home_bar,0,0);
    lv_obj_remove_flag(home_bar,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(home_bar,LV_OBJ_FLAG_CLICKABLE);

    a->widget_rendered_generation=w->generation;
    screen_unlock(a);
}

void screen_ui_widget_refresh(struct screen_app *a)
{
    if(a->page!=PAGE_WIDGET || !a->widget_header_title || !a->widget_list_box) return;
    screen_lock(a);
    const struct screen_widget_state *w=&a->widget;

    if(w->generation==a->widget_rendered_generation) {
        screen_unlock(a);
        return;
    }

    char title_buf[64];
    if(w->done_count>0) snprintf(title_buf,sizeof(title_buf),"Pipeline (%lu Active • %lu Done)",(unsigned long)w->active_count,(unsigned long)w->done_count);
    else snprintf(title_buf,sizeof(title_buf),"Pipeline (%lu Active)",(unsigned long)w->active_count);
    lv_label_set_text(a->widget_header_title,title_buf);

    const lv_font_t *font = (a && a->message_fonts) ? screen_font_get(a->message_fonts, 16) : &a->ui_font;
    if(!font) font = &a->ui_font;

    if(w->count==0) {
        lv_obj_clean(a->widget_list_box);
        lv_obj_t *empty=lv_label_create(a->widget_list_box);
        lv_label_set_text(empty,"No active agents in pipeline.\nPost progress via /api/widget.");
        lv_obj_set_style_text_font(empty,font,0);
        lv_obj_set_style_text_color(empty,lv_color_hex(0x607285),0);
        lv_obj_set_style_text_align(empty,LV_TEXT_ALIGN_CENTER,0);
        lv_obj_set_width(empty,420);
        lv_obj_set_style_pad_top(empty,60,0);
    } else {
        /* Clean empty label if that was the only child */
        if(lv_obj_get_child_count(a->widget_list_box)==1) {
            lv_obj_t *first=lv_obj_get_child(a->widget_list_box,0);
            if(first && lv_obj_check_type(first,&lv_label_class)) {
                lv_obj_clean(a->widget_list_box);
            }
        }

        uint32_t current_children=lv_obj_get_child_count(a->widget_list_box);
        uint32_t update_count=(current_children<w->count)?current_children:w->count;

        /* Slot Reuse: update existing cards in place without deleting/reallocating objects */
        for(uint32_t i=0;i<update_count;i++) {
            lv_obj_t *card=lv_obj_get_child(a->widget_list_box,i);
            update_agent_card(a,card,&w->items[i],i,font);
        }

        /* Append newly added cards */
        lv_obj_t *last_card=NULL;
        for(uint32_t i=current_children;i<w->count;i++) {
            last_card=build_agent_card(a,a->widget_list_box,&w->items[i],i,font);
        }

        /* Remove excess cards if queue shrunk */
        while(lv_obj_get_child_count(a->widget_list_box)>w->count) {
            lv_obj_t *extra=lv_obj_get_child(a->widget_list_box,lv_obj_get_child_count(a->widget_list_box)-1);
            if(extra) lv_obj_delete(extra);
        }

        widget_list_layout(a);
        lv_obj_update_layout(a->widget_list_box);
        bool follow=(lv_obj_get_scroll_bottom(a->widget_list_box)<40) && !a->touch_state.down && !lv_obj_is_scrolling(a->widget_list_box);
        if(last_card && follow) lv_obj_scroll_to_view(last_card,LV_ANIM_OFF);
    }

    a->widget_rendered_generation=w->generation;
    screen_unlock(a);
}
