#include "screen_private.h"
#include <stdio.h>
#include <string.h>
static lv_obj_t *label(lv_obj_t *parent,const char *text,int x,int y,int width)
{
    lv_obj_t *obj=lv_label_create(parent);lv_label_set_text(obj,text);lv_obj_set_pos(obj,x,y);lv_obj_set_width(obj,width);return obj;
}
void screen_ui_messages_remember(screen_app_handle_t a)
{
    if(a->text_list) {
        lv_area_t view; lv_obj_get_coords(a->text_list,&view);
        a->text_follow=lv_obj_get_scroll_bottom(a->text_list)<8;
        for(unsigned p=0;p<a->card_count;p++) {
            lv_area_t card; lv_obj_get_coords(a->cards[p],&card);
            if(card.y2>=view.y1) { a->text_anchor_id=a->card_ids[p]; a->text_anchor_offset=card.y1-view.y1; break; }
        }
    }
}
static void restore_scroll(screen_app_handle_t a)
{
    lv_obj_t *view=a->text_list;lv_obj_update_layout(view);
    if(a->text_reveal_id) {
        for(unsigned p=0;p<a->card_count;p++)if(a->card_ids[p]==a->text_reveal_id || p==a->card_count-1) {
            lv_obj_scroll_to_y(view,lv_obj_get_y(a->cards[p]),LV_ANIM_OFF);break;
        }
        a->text_reveal_id=0;a->text_follow=lv_obj_get_scroll_bottom(view)<8;
    } else if(a->text_follow) {
        lv_obj_scroll_to_y(view,lv_obj_get_scroll_y(view)+lv_obj_get_scroll_bottom(view),LV_ANIM_OFF);
    } else {
        bool found=false;
        for(unsigned p=0;p<a->card_count;p++)if(a->card_ids[p]==a->text_anchor_id) {
            lv_obj_scroll_to_y(view,lv_obj_get_y(a->cards[p])-a->text_anchor_offset,LV_ANIM_OFF);found=true;break;
        }
        if(!found)lv_obj_scroll_to_y(view,0,LV_ANIM_OFF); /* anchor expired */
    }
}
static void create_card(screen_app_handle_t a,unsigned pos,const screen_entry_t *entry,const struct screen_message *m)
{
    lv_obj_t *card=lv_obj_create(a->text_list);a->cards[pos]=card;a->card_ids[pos]=entry->id;
    lv_obj_set_width(card,440);lv_obj_remove_flag(card,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_pad_all(card,12,0);lv_obj_set_style_border_width(card,0,0);
    lv_obj_set_style_bg_color(card,lv_color_hex(0x1c2836),0);lv_obj_set_style_text_color(card,lv_color_hex(0xf0f4fa),0);
    lv_obj_t *time=label(card,entry->time,0,0,350);lv_obj_set_style_text_color(time,lv_color_hex(0xa5b5c9),0);
    a->marks[pos]=label(card,entry->read?LV_SYMBOL_OK:LV_SYMBOL_BULLET,386,0,24);
    lv_obj_set_style_text_font(a->marks[pos],&lv_font_montserrat_20,0);
    lv_obj_set_style_text_color(a->marks[pos],lv_color_hex(entry->read?0x778899:0x39e69d),0);
    lv_obj_t *body=label(card,m->text,0,34,416);a->text=body;lv_obj_set_user_data(card,body);
    lv_obj_set_style_text_font(body,screen_font_get(a->message_fonts,m->font_size),0);
    lv_obj_set_style_text_line_space(body,(2*m->font_size+8)/16,0);
    lv_obj_set_style_text_align(body,m->align==1?LV_TEXT_ALIGN_CENTER:m->align==2?LV_TEXT_ALIGN_RIGHT:LV_TEXT_ALIGN_LEFT,0);
    lv_obj_update_layout(body);lv_obj_set_height(card,lv_obj_get_height(body)+64);
}
void screen_ui_messages_sync(screen_app_handle_t a)
{
    if(!a->text_list)return;
    if(a->card_count)screen_ui_messages_remember(a);
    struct screen_messages_snapshot *value=a->ui_messages;
    screen_lock(a);value->history=a->messages;memcpy(value->messages,a->messages_data,sizeof(value->messages));screen_unlock(a);
    for(unsigned p=0;p<a->card_count;) {
        if(screen_history_find(&value->history,a->card_ids[p])>=0){p++;continue;}
        lv_obj_delete(a->cards[p]);a->card_count--;
        for(unsigned k=p;k<a->card_count;k++){a->cards[k]=a->cards[k+1];a->marks[k]=a->marks[k+1];a->card_ids[k]=a->card_ids[k+1];}
    }
    int y=0;
    for(unsigned pos=0;pos<value->history.count;pos++) {
        int i=screen_history_at(&value->history,pos);
        if(pos>=a->card_count) {create_card(a,pos,&value->history.entries[i],&value->messages[i]);a->card_count++;}
        lv_obj_set_pos(a->cards[pos],4,y);lv_obj_update_layout(a->cards[pos]);y+=lv_obj_get_height(a->cards[pos])+12;
    }
    if(a->card_count && a->messages_empty){lv_obj_delete(a->messages_empty);a->messages_empty=NULL;}
    else if(!a->card_count && !a->messages_empty)a->messages_empty=label(a->text_list,"Waiting for pushed messages...",16,120,424);
    a->text_generation=value->history.generation;a->text_unread=screen_history_unread(&value->history);
    char count[40];snprintf(count,sizeof(count),"%u unread",a->text_unread);lv_label_set_text(a->unread_label,count);
    restore_scroll(a);
}
void screen_ui_messages_build(screen_app_handle_t a,lv_obj_t *root)
{
    label(root,"MESSAGES",24,20,120);
    a->unread_label=label(root,"",148,20,140);
    screen_ui_draw_page_dots(a, root, 3, 5);
    a->text_list=lv_obj_create(root);lv_obj_t *view=a->text_list;
    lv_obj_set_pos(view,12,62);lv_obj_set_size(view,456,386);
    lv_obj_set_style_pad_all(view,0,0);lv_obj_set_style_border_width(view,0,0);lv_obj_set_style_bg_opa(view,LV_OPA_TRANSP,0);
    lv_obj_set_scroll_dir(view,LV_DIR_VER);lv_obj_set_scrollbar_mode(view,LV_SCROLLBAR_MODE_AUTO);
    label(root,"< Pictures",20,450,200);a->message_notice=label(root,"",264,450,200);
    lv_obj_set_style_text_color(a->message_notice,lv_color_hex(0x39e69d),0);
    screen_ui_messages_sync(a);lv_obj_invalidate(root);
}
void screen_ui_read_tick(struct screen_app *a,int64_t now,bool touching)
{
    if(a->page!=PAGE_TEXT || !a->text_list)return;
    lv_obj_update_layout(a->text_list);a->text_follow=lv_obj_get_scroll_bottom(a->text_list)<8;
    lv_area_t view;lv_obj_get_coords(a->text_list,&view);
    bool moving=touching || lv_obj_is_scrolling(a->text_list);
    for(unsigned p=0;p<a->card_count;p++) {
        lv_area_t body;lv_obj_get_coords(lv_obj_get_user_data(a->cards[p]),&body);
        int start=view.y1>body.y1?view.y1-body.y1:0;
        int end=view.y2<body.y2?view.y2-body.y1+1:body.y2-body.y1+1;
        bool changed=false;screen_lock(a);int i=screen_history_find(&a->messages,a->card_ids[p]);
        if(i>=0) {screen_entry_t *e=&a->messages.entries[i];if(moving)e->exposure_us=0;else changed=screen_entry_expose(e,start,end,body.y2-body.y1+1,now);}
        screen_unlock(a);
        if(changed){lv_label_set_text(a->marks[p],LV_SYMBOL_OK);lv_obj_set_style_text_color(a->marks[p],lv_color_hex(0x778899),0);}
    }
    screen_lock(a);unsigned unread=screen_history_unread(&a->messages);screen_unlock(a);
    if(unread!=a->text_unread) {a->text_unread=unread;char count[40];snprintf(count,sizeof(count),"%u unread",unread);lv_label_set_text(a->unread_label,count);}
}
