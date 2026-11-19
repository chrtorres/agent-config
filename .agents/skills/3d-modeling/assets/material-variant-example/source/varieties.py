"""Original pigment layouts inspired by the JNPA variety standards."""
import numpy as np

VARIETIES = {
    "kohaku": ("Kōhaku", "Pearl white with three scarlet plates"),
    "sanke": ("Taishō Sanke", "White ground, scarlet plates and isolated lacquer-black spots"),
    "showa": ("Shōwa Sanshoku", "Black wraps across the face and flanks, with red and white plates"),
    "asagi": ("Asagi", "Indigo-blue scale centers with pale edging and red along the lower flanks"),
    "ogon": ("Yamabuki Ōgon", "Unpatterned golden-yellow skin with a metallic sheen"),
}


def smooth(a, b, value):
    weight = np.clip((value-a)/(b-a), 0, 1)
    return weight*weight*(3-2*weight)


def mix(first, second, weight):
    first, second = np.asarray(first), np.asarray(second)
    return first + (second-first)*weight[..., None]


def patches(x, theta, outlines, irregularity):
    # Wrap angular distance around the belly seam so patches can cross it.
    field = np.full(np.broadcast_shapes(x.shape,theta.shape),-20,dtype=np.float32)
    for cx, ca, rx, ra, lean in outlines:
        a = (theta-ca+np.pi)%(2*np.pi)-np.pi
        shape = 1-((x-cx+lean*a+.035*np.sin(5*a+2*cx))/rx)**2-(a/ra)**2
        field = np.maximum(field,shape)
    return smooth(-.035,.038,field+irregularity)


def skin_color(variety,x,a,scales):
    edge,crown,grain,circuli,overlap = scales
    top = np.cos(a)
    pale = np.array([.915,.885,.822],dtype=np.float32)
    red = np.array([.634,.066,.034],dtype=np.float32)
    black = np.array([.071,.076,.082],dtype=np.float32)
    milk = mix([.88,.815,.747],pale,smooth(-1,.55,top))
    cloud = .5+.5*np.sin(5*x+3*a)*np.sin(3*x-2*a)
    wave = .078*np.sin(17*x+7*a)+.046*np.sin(29*x-13*a)+.032*np.cos(43*x+8*a)
    # Areas of visible scales scallop the pigment edges by a fraction of one scale.
    boundary = wave+.060*(crown-edge)*overlap
    red_mix = mix(red,[.767,.140,.058],cloud*.65)
    rough = .345+0*x+0*a
    if variety=="kohaku":
        scarlet = patches(x,a,[(-2.08,-.05,.61,1.20,-.12),
                              (-.60,.25,.64,1.69,.19),(.97,-.40,.63,1.44,-.22)],boundary)
        color = mix(milk,red_mix,scarlet)
        rough -= .030*scarlet
    elif variety=="sanke":
        scarlet = patches(x,a,[(-2.18,.10,.45,1.08,.13),
                               (-1.18,-.51,.36,1.08,-.14),
                               (-.36,.60,.46,1.16,.08),(.92,-.20,.63,1.48,-.19)],boundary)
        ink = patches(x,a,[(-1.42,.61,.30,.56,.17),(-1.11,-1.09,.15,.34,-.12),
                           (-.70,-.22,.27,.40,.14),(-.17,-1.30,.23,.34,.09),
                           (.16,.92,.21,.50,-.12),(.61,.38,.25,.43,-.16),
                           (1.29,-.88,.14,.43,.18)],boundary)
        color = mix(mix(milk,red_mix,scarlet),black,ink)
        rough -= .024*scarlet+.040*ink
    elif variety=="showa":
        scarlet = patches(x,a,[(-2.25,-.25,.49,1.42,-.10),(-1.10,.12,.72,1.19,.12),
                               (-.12,-1.04,.41,.84,-.19),(1.18,.35,.43,1.25,.22)],boundary)
        ink = patches(x,a,[(-2.33,.58,.22,1.60,-.18),(-1.64,2.4,.45,1.70,-.18),
                           (-.84,-1.56,.32,1.91,.16),(-.28,.53,.31,1.55,-.20),
                           (.43,2.48,.37,1.68,.15),(.86,-.67,.33,1.72,-.21),
                           (1.70,.53,.32,1.66,.17)],boundary)
        color = mix(mix(milk,red_mix,scarlet),black,ink)
        rough -= .021*scarlet+.040*ink
    elif variety=="asagi":
        blue = smooth(-.99,-.38,top)*smooth(-1.95,-1.56,x)
        net = np.clip(.14+.48*edge+.44*(1-crown)*overlap,0,1)
        blue_scales = mix([.18,.32,.43],[.63,.74,.76],net)
        belly_height = -.61+.115*np.sin(3.3*x+1.9*a)+.047*np.sin(19*x-6*a)
        belly = smooth(belly_height+.14,belly_height-.13,top)*smooth(-2.27,-1.84,x)
        belly *= 1-smooth(1.86,2.29,x)
        cheeks = patches(x,a,[(-1.99,1.88,.29,.44,-.15),(-2.03,-1.92,.26,.49,.10)],wave)
        color = mix(mix(milk,blue_scales,blue),[.81,.241,.107],np.maximum(belly,cheeks))
        rough += .023*blue
    else:
        gold = mix([.79,.50,.124],[.97,.723,.23],smooth(-1,.66,top))
        color = mix(gold,[.987,.792,.337],.19*crown+.16*cloud)
        rough -= .077
    return color,rough


def fin_color(variety,name,along,span,base):
    pectoral = "pectoral" in name
    paired = pectoral or "pelvic" in name
    if variety=="sanke" and (pectoral or "Caudal" in name):
        stripe = np.exp(-((along-.35)/.048)**2)+.8*np.exp(-((along-.63)/.033)**2)
        streak = .72*stripe*smooth(.12,.27,span)*(1-smooth(.67,.95,span))
        return mix(base,[.073,.084,.094],streak)
    if variety=="showa" and pectoral:
        black_root = 1-smooth(.24,.44,span+.064*np.sin(18*along)+.081*np.cos(6*along))
        return mix(base,[.042,.053,.065],black_root*.94)
    if variety=="asagi" and paired:
        blaze = 1-smooth(.30,.79,span+.08*np.sin(17*along)+.07*np.cos(4*along))
        return mix(base,[.73,.167,.076],blaze*.92)
    if variety=="ogon":
        return base*np.array([1.05,.80,.34])+np.array([.025,.032,.010])
    return base
