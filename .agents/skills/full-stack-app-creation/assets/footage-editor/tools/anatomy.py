"""Fit smaller visible supports on the existing source-pixel anatomy tracks."""
import math


AXIAL = {
    "hair": ("Hair", "head"),
    "neck": ("Neck", "torso"),
    "abdomen": ("Abdomen", "torso"),
    "waist": ("Waist", "torso"),
    "upper-back": ("Upper back", "torso"),
    "lower-back": ("Lower back", "torso"),
}

FACE_DETAIL = {
    "forehead": ("Forehead", "head"),
    "nose-bridge": ("Nose bridge", "nose"),
    "nose-tip": ("Nose tip", "nose"),
    "upper-lip": ("Upper lip", "mouth"),
    "lower-lip": ("Lower lip", "mouth"),
    "jawline": ("Jawline", "head"),
}

SIDE_DETAIL = {
    "ear": ("ear", "head"),
    "cheek": ("cheek", "head"),
    "temple": ("temple", "head"),
    "upper-eyelid": ("upper eyelid", "{side}-eye"),
    "lower-eyelid": ("lower eyelid", "{side}-eye"),
    "nostril": ("nostril", "nose"),
    "shoulder": ("shoulder", "shoulders"),
    "flank": ("flank", "waist"),
    "upper-arm": ("upper arm", "{side}-arm"),
    "elbow": ("elbow", "{side}-arm"),
    "forearm": ("forearm", "{side}-arm"),
    "wrist": ("wrist", "{side}-arm"),
    "palm": ("palm", "{side}-hand"),
    "thigh": ("thigh", "{side}-leg"),
    "knee": ("knee", "{side}-leg"),
    "shin": ("shin", "{side}-calf"),
    "ankle": ("ankle", "{side}-leg"),
    "heel": ("heel", "{side}-foot"),
    "foot": ("foot", "{side}-leg"),
    "toe-area": ("toe area", "{side}-foot"),
}

DIGIT_DETAILS = {"base": "base", "joint": "joint", "tip": "tip"}


def catalog(sides, fingers, hands=True):
    details = {**AXIAL, **FACE_DETAIL}
    for side in sides:
        for key, (label, parent) in SIDE_DETAIL.items():
            if not hands and key == "palm":
                continue
            details[f"{side}-{key}"] = (f"{side.title()} {label}", parent.format(side=side))
        if hands:
            for finger, (label, _) in fingers.items():
                for key, part in DIGIT_DETAILS.items():
                    details[f"{side}-{finger}-{key}"] = (f"{side.title()} {label} {part}", f"{side}-{finger}")
    return details


def blend(a, b, ratio):
    return tuple(a[i] + (b[i] - a[i])*ratio for i in (0, 1))


def direction(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    return (dx/length, dy/length, length) if length > 1 else (1., 0., length)


def place(result, key, center, axes, rx, ry, foreground):
    if not foreground(center):
        return
    result[key] = [[round(value, 3) for value in (*center[:2], *axes[:2], max(2.5, rx), max(3., ry))]]


def along(result, key, a, b, fraction, width, extent, foreground, confidence=40):
    if min(a[2], b[2]) < confidence:
        return
    ux, uy, length = direction(a,b)
    center = blend(a,b,fraction)
    if length<12 or not any(foreground(blend(a,b,t)) for t in (max(0,fraction-.18),min(1,fraction+.18))):
        return
    place(result,key,center,(-uy,ux),length*width,length*extent,foreground)


def pose_details(points, foreground):
    result = {}
    ls, rs, lh, rh = (points[i] for i in (11, 12, 23, 24))
    shoulders, hips = blend(ls,rs,.5), blend(lh,rh,.5)
    across_x, across_y, span = direction(rs,ls)
    tx, ty, trunk = direction(shoulders,hips)
    ears = blend(points[7],points[8],.5)
    _, _, ear_span = direction(points[7],points[8])
    if min(ls[2],rs[2])>=38 and span>=25:
        nx,ny,neck = direction(ears,shoulders)
        if min(points[7][2],points[8][2])>=25 and neck>=17 and ny>.45:
            place(result,"neck",blend(ears,shoulders,.68),(-ny,nx),span*.16,neck*.42,foreground)
    if min(points[7][2],points[8][2])>=33 and ear_span>=16 and trunk>=35 and ty>.5:
        crown = (ears[0]-tx*ear_span*.67,ears[1]-ty*ear_span*.67)
        place(result,"hair",crown,(across_x,across_y),ear_span*.68,ear_span*.63,foreground)
    if min(ls[2],rs[2],lh[2],rh[2])>=42 and span>=24 and trunk>=45 and ty>.5:
        across = (-ty,tx)
        hip_span = math.dist(lh[:2],rh[:2])
        if hip_span>=.18*trunk and span>=.28*trunk:
            place(result,"waist",blend(shoulders,hips,.71),across,span*.43,trunk*.20,foreground)
        front = ls[0]-rs[0]>.30*trunk and lh[0]-rh[0]>.21*trunk
        rear = rs[0]-ls[0]>.30*trunk and rh[0]-lh[0]>.21*trunk
        if front:
            place(result,"abdomen",blend(shoulders,hips,.63),across,span*.39,trunk*.23,foreground)
        if rear:
            place(result,"upper-back",blend(shoulders,hips,.31),across,span*.47,trunk*.26,foreground)
            place(result,"lower-back",blend(shoulders,hips,.67),across,span*.42,trunk*.21,foreground)
        if front or rear:
            for side,shoulder,hip in (("left",ls,lh),("right",rs,rh)):
                flank=blend(shoulder,hip,.69)
                center=blend(flank,blend(shoulders,hips,.69),.16)
                place(result,f"{side}-flank",center,across,span*.18,trunk*.24,foreground)

    for side,i in (("left",0),("right",1)):
        shoulder,elbow,wrist = (points[j+i] for j in (11,13,15))
        hip,knee,ankle,heel,toe = (points[j+i] for j in (23,25,27,29,31))
        for key,a,b,t,width,extent in (
            ("shoulder",shoulder,elbow,.11,.27,.27),
            ("upper-arm",shoulder,elbow,.45,.26,.52),
            ("elbow",shoulder,elbow,.92,.22,.23),
            ("forearm",elbow,wrist,.49,.24,.56),
            ("wrist",elbow,wrist,.93,.20,.24),
            ("thigh",hip,knee,.46,.33,.56),
            ("knee",hip,knee,.93,.26,.25),
            ("shin",knee,ankle,.60,.19,.41),
            ("ankle",knee,ankle,.93,.18,.23),
            ("foot",heel,toe,.49,.29,.65),
            ("heel",heel,toe,.09,.27,.28),
            ("toe-area",heel,toe,.87,.27,.29),
        ):
            along(result,f"{side}-{key}",a,b,t,width,extent,foreground)

        # The farther ear of a profile can be predicted on top of the near
        # cheek. Suppress it when nose-to-ear distances are highly asymmetric.
        ear = points[7+i]
        nose, other = points[0], points[8-i]
        to_nose = math.dist(nose[:2],ear[:2])
        other_to_nose = math.dist(nose[:2],other[:2])
        if min(ear[2],nose[2])>=53 and to_nose>=11 and to_nose>=other_to_nose*.54:
            ux,uy,_ = direction(nose,ear)
            place(result,f"{side}-ear",ear,(ux,uy),to_nose*.16,to_nose*.25,foreground)
    return result


def facial_details(pixels, baseline, foreground):
    result = {}
    ex, ey, span = baseline
    face_axis = (ex,ey)
    def point(key, ids, width, height):
        center=tuple(sum(pixels[index][axis] for index in ids)/len(ids) for axis in (0,1))
        place(result,key,center,face_axis,span*width,span*height,foreground)

    for key,ids,rx,ry in (
        ("forehead",(10,151,9),.39,.22),
        ("nose-bridge",(168,6,197),.12,.23),
        ("nose-tip",(1,2,4),.16,.14),
        ("upper-lip",(0,13,37,267),.31,.085),
        ("lower-lip",(14,17,84,314),.31,.09),
        ("jawline",(152,172,397),.54,.18),
    ):
        point(key,ids,rx,ry)

    # Profile views collapse the far-side intervals; the detector still
    # returns points there, so projected width is part of their visibility.
    for side,eye,cheek,temple,lids,nostril in (
        ("left",(362,263),(280,330,347),(251,389,368),((386,385),(374,380)),(327,326)),
        ("right",(133,33),(50,101,118),(21,162,139),((159,160),(145,144)),(98,97)),
    ):
        width=math.dist(pixels[eye[0]],pixels[eye[1]])
        if width < span*.19:
            continue
        point(f"{side}-cheek",cheek,.22,.25)
        point(f"{side}-temple",temple,.18,.23)
        point(f"{side}-upper-eyelid",lids[0],width/span*.53,.075)
        point(f"{side}-lower-eyelid",lids[1],width/span*.53,.075)
        point(f"{side}-nostril",nostril,.095,.09)
    return result


def hand_details(side, hand, fingers, across, foreground):
    result = {}
    ux,uy,length = direction(hand[0],hand[9])
    place(result,f"{side}-palm",blend(hand[0],hand[9],.56),(-uy,ux),across*.61,length*.62,foreground)
    for finger,(_,indices) in fingers.items():
        a,b,c,d = (hand[i] for i in indices)
        if sum(foreground(point) for point in (b,c,d)) < 2:
            continue
        for key, start, end, t in (("base",a,b,.5),("joint",b,c,.54),("tip",c,d,.78)):
            dx,dy,segment = direction(start,end)
            if segment<3:
                continue
            place(result,f"{side}-{finger}-{key}",blend(start,end,t),
                  (-dy,dx),min(across*.21,segment*.54),segment*.67,foreground)
    return result


def detail_anchors(points, regions, parents, references):
    """Choose the visible bone or local feature frame for a detail track."""
    result={}
    for key,parent in parents.items():
        if key not in regions:
            continue
        side,_,part=key.partition("-")
        axes=references.get(parent,[])
        anchor=next((axis for axis in axes if axis is not None),None)
        if side in ("left","right"):
            offset=int(side=="right")
            if part in ("upper-arm","elbow","forearm","wrist","shoulder"):
                a,b=(13,15) if part in ("forearm","wrist") else (11,13)
            elif part in ("thigh","knee","shin","ankle"):
                a,b=(25,27) if part in ("shin","ankle") else (23,25)
            elif part in ("foot","heel","toe-area"):
                a,b=29,31
            else:
                a=b=None
            if a is not None:
                start,end=points.get(a+offset),points.get(b+offset)
                if start and end and min(start[2],end[2])>=38 and math.dist(start[:2],end[:2])>=12:
                    anchor=[*start[:2],*end[:2]]

        qualifier=key.removeprefix(parent+"-")
        if qualifier in DIGIT_DETAILS:
            supports=regions.get(parent)
            if supports and supports[0]:
                x,y,ux,uy,_,length=supports[0]
                extent=max(8,length)
                anchor=[x,y,x+uy*extent,y-ux*extent]
        if parent=="waist":
            anchor=next((axis for axis in references.get("torso",[]) if axis is not None),None)
        if parent=="head" and key!="hair" and part!="ear":
            anchor=next((axis for axis in references.get("nose",[]) if axis is not None),anchor)
        if anchor is not None:
            result[key]=[anchor if shape is not None else None for shape in regions[key]]
    return result
