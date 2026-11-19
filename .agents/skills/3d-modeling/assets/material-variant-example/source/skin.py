"""Rasterize the shared skin surface into portable PBR textures."""
import bpy
import numpy as np

from varieties import skin_color, smooth


def packed_image(name, pixels, data=False):
    height,width,_ = pixels.shape
    image = bpy.data.images.new(name,width=width,height=height,alpha=False)
    if data:
        image.colorspace_settings.name = "Non-Color"
    rgba=np.empty((height,width,4),dtype=np.float32)
    rgba[:,:,:3]=pixels
    rgba[:,:,:3]*=1/255
    rgba[:,:,3]=1
    image.pixels.foreach_set(rgba.ravel())
    image.update()
    image.pack()
    return image


def value_noise(x, theta, density, rows, seed):
    """Interpolate a deterministic, circumferentially periodic lattice."""
    tx,ty=(x+3)*density,(theta+np.pi)*(rows/(2*np.pi))
    ix,iy=np.floor(tx),np.floor(ty)
    fx,fy=smooth(0,1,tx-ix),smooth(0,1,ty-iy)
    def corner(dx,dy):
        phase=np.sin((ix+dx)*127.1+((iy+dy)%rows)*311.7+seed*7.3)*43758.5453
        return 2*(phase-np.floor(phase))-1

    bottom=corner(0,0)*(1-fx)+corner(1,0)*fx
    top=corner(0,1)*(1-fx)+corner(1,1)*fx
    return bottom*(1-fy)+top*fy


def generate_skin(variety, profile, scale_field, gill_field, nare_field, width):
    w,h=width,width//2
    u=((np.arange(w,dtype=np.float32)+.5)/w)[None,:]
    x,ry,top,bottom,zc=np.moveaxis(profile(u),-1,0)
    xstep=np.maximum(np.abs(np.gradient(x,axis=1)),.00048)
    color_map=np.empty((h,w,3),dtype=np.uint8)
    normal_map=np.empty_like(color_map)
    # Pack linear roughness and metalness in the glTF channels.
    surface_map=np.empty_like(color_map)
    a_all=np.linspace(-np.pi,np.pi,h,endpoint=False,dtype=np.float32)+np.pi/h
    for start in range(0,h,32):
        end=min(start+32,h)
        with_border=(np.arange(start-1,end+1)%h)
        a=a_all[with_border,None]
        edge,crown,grain,circuli,overlap=scale_field(x,a)
        pigment,rough=skin_color(variety,x,a,(edge,crown,grain,circuli,overlap))
        fine=.65*value_noise(x,a,48,123,3)+.35*value_noise(x,a,103,218,7)
        mottling=value_noise(x,a,12,31,2)
        variation=.009*mottling+.006*fine-.016*edge+.014*crown+.018*grain+.007*circuli
        cheek= np.exp(-((x+2.06)/.35)**2-((np.abs(a)-1.88)/.61)**2)
        pigment += variation[...,None]+.07*cheek[...,None]*np.array([.48,-.17,-.34])
        gill_distance,gill_gate=gill_field(x,a)
        gill=np.exp(-(gill_distance/.021)**2)*gill_gate
        pigment-=gill[...,None]*np.array([.080,.124,.141])
        pore_line=np.exp(-((np.cos(a)-.12-.047*np.sin(2*x))/.030)**2)*overlap
        pores=np.exp(-((np.sin(np.pi*np.interp(x,[-1.9,-.6,.65,1.5,2.3],[0,8,17,24,34])))/.27)**2)*pore_line
        pigment-=pores[...,None]*np.array([.075,.091,.097])
        nares,nare_rims=nare_field(x,a)
        pigment-=nares[...,None]*np.array([.27,.31,.32])
        pigment+=nare_rims[...,None]*np.array([.068,.037,.032])
        throat=1-smooth(.068,.185,u)
        vermilion=.30*np.exp(-((u-.205)/.043)**2)
        pigment=pigment*(1-throat[...,None])+np.array([.163,.057,.070])*throat[...,None]
        pigment=pigment*(1-vermilion[...,None])+np.array([.82,.54,.47])*vermilion[...,None]
        color_map[start:end]=np.rint(np.clip(pigment[1:-1],0,1)*255).astype(np.uint8)
        rough+=.035*edge-.036*crown+.021*fine+.023*overlap+.035*nares
        surface_map[start:end,:,0]=255
        surface_map[start:end,:,1]=np.rint(np.clip(rough[1:-1],.19,.53)*255).astype(np.uint8)
        surface_map[start:end,:,2]=82 if variety=="ogon" else 0

        # Macro scale lips live in geometry. This map adds lower relief growth rings and grit.
        height=.00046*circuli+.00029*fine+.00046*crown-.00034*edge-.00065*pores
        du=np.gradient(height,axis=1)[1:-1]/xstep
        c,s=np.cos(a[1:-1]),np.sin(a[1:-1])
        dv_radius=np.hypot(ry*c,np.where(c>=0,top,bottom)*s)
        dv=(height[2:]-height[:-2])/(4*np.pi/h*np.maximum(dv_radius,.065))
        inv=1/np.sqrt(1+du*du+dv*dv)
        normal=np.stack([-du*inv,-dv*inv,inv],axis=-1)*.5+.5
        normal_map[start:end]=np.rint(np.clip(normal,0,1)*255).astype(np.uint8)
    return (
        packed_image(variety+" • skin pigment",color_map),
        packed_image("Skin • tangent microstructure",normal_map,True),
        packed_image(variety+" • surface gloss",surface_map,True),
    )
