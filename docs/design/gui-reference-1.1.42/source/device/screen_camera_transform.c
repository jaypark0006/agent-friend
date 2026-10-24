#include "screen_camera_transform.h"
screen_camera_transform_t screen_camera_transform(int mount_cw_deg,bool mirror_x,int display_cw_deg)
{
    int angle=mount_cw_deg+(mirror_x?display_cw_deg:-display_cw_deg);
    angle=(angle%360+360)%360;
    return (screen_camera_transform_t){angle,mirror_x};
}
int screen_camera_frame_rotation(int display_rotation_cw_deg)
{
    return screen_camera_transform(SCREEN_CAMERA_MOUNT_ROTATION_CW_DEG,SCREEN_CAMERA_MOUNT_MIRROR_X,display_rotation_cw_deg).rotation_cw_deg;
}
size_t screen_camera_source_pixel(unsigned x,unsigned y,unsigned side,screen_camera_transform_t t)
{
    if(t.mirror_x)x=side-1-x;
    switch(t.rotation_cw_deg) {
    case 90:return (side-1-x)*side+y;
    case 180:return (side-1-y)*side+(side-1-x);
    case 270:return x*side+(side-1-y);
    default:return y*side+x;
    }
}
