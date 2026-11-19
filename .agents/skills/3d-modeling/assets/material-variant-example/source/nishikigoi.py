"""Generate a nishikigoi variety, studio renders and an asset-only GLB.

blender -b --factory-startup -t 5 --python-exit-code 1 --python source/nishikigoi.py -- --version <revision> --variety kohaku --output <variant-directory>
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from skin import generate_skin
from varieties import VARIETIES, fin_color, smooth

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--length-mm", type=float, default=700)
parser.add_argument("--skip-renders", action="store_true")
parser.add_argument("--version", required=True)
parser.add_argument("--texture-width", type=int, choices=(512,1024,2048,4096), default=4096)
parser.add_argument("--samples", type=int, default=20)
parser.add_argument("--variety", choices=VARIETIES, default="kohaku")
parser.add_argument("--preview-percent", type=int, choices=range(25,101), default=100)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
if args.samples < 1:
    parser.error("--samples must be positive")
if not math.isfinite(args.length_mm) or args.length_mm <= 0:
    parser.error("--length-mm must be a finite positive number")
OUT = args.output.resolve()
VARIETY = args.variety
TITLE, DESCRIPTION = VARIETIES[VARIETY]
for folder in ("preview", "review", "evidence"):
    (OUT / folder).mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
asset = bpy.data.collections.new("Nishikigoi anatomy")
scene.collection.children.link(asset)
studio = bpy.data.collections.new("Studio")
scene.collection.children.link(studio)

# Axial stations describe the body before it is bent into a single swimming pose.
# The first stations fold back into the mouth to form an actual oral cavity.
# x, half width, dorsal depth, ventral depth, vertical center
PROFILE = np.array([
    [-2.72,.018,.010,.009,-.177], [-2.75,.084,.035,.028,-.172],
    [-2.86,.134,.044,.037,-.180], [-2.98,.144,.046,.039,-.180],
    [-3.00,.163,.067,.057,-.158], [-2.93,.191,.103,.093,-.118],
    [-2.77,.243,.166,.138,-.072], [-2.54,.326,.264,.215,-.028],
    [-2.24,.405,.365,.297,.004], [-1.92,.468,.471,.387,.025],
    [-1.55,.528,.535,.463,.025], [-1.10,.539,.563,.494,.031],
    [-.65,.494,.545,.475,.040], [-.15,.437,.497,.415,.048],
    [.37,.356,.416,.337,.056], [.85,.270,.330,.252,.059],
    [1.25,.191,.252,.181,.065], [1.68,.116,.167,.127,.068],
    [2.02,.077,.128,.112,.070], [2.23,.063,.115,.099,.072],
    [2.30,.028,.075,.060,.072],
], dtype=np.float32)


def spline(knots, parameters):
    """Cubic Hermite interpolation through editable landmarks."""
    t = np.asarray(parameters)
    i = np.clip((t*(len(knots)-1)).astype(int), 0, len(knots)-2)
    f = (t*(len(knots)-1)-i)[..., None]
    left, right = knots[i], knots[i+1]
    before = knots[np.maximum(i-1, 0)]
    after = knots[np.minimum(i+2, len(knots)-1)]
    m0, m1 = (right-before)*.5, (after-left)*.5
    return left + f*(m0+f*(3*(right-left)-2*m0-m1+f*(2*(left-right)+m0+m1)))


def axial_parameter(x):
    # The exterior is monotonic after the lip. Use it to anchor features to the skin.
    return np.interp(x, PROFILE[4:,0], np.arange(4,len(PROFILE))/(len(PROFILE)-1))


def pose(points):
    """Bend longitudinal sections together, keeping local fin roots attached."""
    x, y, z = np.moveaxis(np.asarray(points), -1, 0)
    t = (x+3)/6.6
    center = -.117*np.sin(1.65*np.pi*t)+.60*t**3
    tangent = (-.117*1.65*np.pi*np.cos(1.65*np.pi*t)+1.80*t*t)/6.6
    norm = np.sqrt(1+tangent*tangent)
    return np.stack((x-y*tangent/norm, center+y/norm, z+.035*np.sin(2*np.pi*t+.4)), axis=-1)


def skin_scales(x, theta):
    """Return scale edges, crowns, pigment variation and arcs on a shared staggered lattice."""
    rows = 30
    axial = np.interp(x,[-3,-1.95,-1.25,-.30,.65,1.50,2.32],[-8,0,4.5,10.8,17.8,25.1,35.8])
    angular = theta*(rows/(2*np.pi)) + .27*np.sin(theta)*np.sin(2.1*x)
    best = np.full(np.broadcast_shapes(x.shape,theta.shape),9,dtype=np.float32)
    phase = np.zeros_like(best)
    roll = np.zeros_like(best)
    crosswise = np.zeros_like(best)
    # Curved tailward edges can cross the cells of the staggered lattice.
    for offset in (-1,0,1):
        row = np.floor(angular+.5)+offset
        wrapped = row%rows
        cross = angular-row
        shift = row*.5 + .045*np.sin(2*np.pi*wrapped*7/rows)
        front = axial-shift-.59*np.maximum(0,1-(cross/.70)**2)
        column = np.round(front)
        signed = front-column
        distance = np.abs(signed)
        valid = (np.abs(cross)<.59) & (distance<best)
        roll = np.where(valid,signed,roll)
        crosswise = np.where(valid,cross,crosswise)
        phase = np.where(valid,np.sin(67.13*(column+np.floor(row/rows)*15)+113.17*wrapped),phase)
        best = np.where(valid,distance,best)
    first = -1.94+.19*np.abs(np.sin(theta))+.16*np.cos(theta)
    fade = smooth(first,first+.25,x)*(1-.87*smooth(-.39,-.98,np.cos(theta)))*(1-smooth(2.12,2.28,x))
    edge = np.exp(-(best/.055)**2)*fade
    crown = np.exp(-((roll+.22)/.25)**2)*fade
    # Rows of faint, irregular circuli follow the exposed trailing edge of each scale.
    circuli = np.cos((roll+.047*crosswise**2)*np.pi*18+.75*phase)
    circuli *= fade*smooth(-.50,-.12,roll)*(1-smooth(-.08,.083,roll))
    return edge,crown,phase*fade,circuli,fade


def gill_mask(x, theta):
    side = np.abs(np.sin(theta))
    height = np.cos(theta)
    gill_x = -1.93+.15*height+.135*np.sin(3.24*height)-.032*np.sin(theta)
    return x-gill_x,smooth(.39,.82,side)


def nare_field(x, theta):
    # Carp have two openings in each olfactory chamber. The anterior opening is smaller.
    angle = np.abs(theta)
    front = ((x+2.723)/.030)**2+((angle-.83)/.092)**2
    back = ((x+2.623+.047*(angle-.71))/.040)**2+((angle-.76)/.11)**2
    pit = np.maximum(np.exp(-front),np.exp(-back))
    rim = np.maximum(np.exp(-((front-1.2)/.61)**2),np.exp(-((back-1.28)/.65)**2))
    return pit,rim


def body_surface(u, theta, relief=True):
    x,ry,top,bottom,zc = np.moveaxis(spline(PROFILE,u),-1,0)
    c,s = np.cos(theta),np.sin(theta)
    detail=0
    if relief:
        edge,crown,grain,_,_ = skin_scales(x,theta)
        d,gate = gill_mask(x,theta)
        lateral = np.exp(-((c-.12-.047*np.sin(2*x))/.038)**2)
        nares,nare_rims = nare_field(x,theta)
        lip_flute = np.exp(-((u-.20)/.037)**2)*(.5+.5*np.cos(14*theta+1.9*np.sin(theta)))
        root = np.exp(-((x+1.78)/.24)**2-((np.abs(theta)-2.13)/.25)**2)
        detail = ((.0037+.0011*grain)*crown-.0019*edge
                  +gate*(.016*np.exp(-((d+.080)/.065)**2)-.015*np.exp(-(d/.019)**2))
                  -.0020*lateral*smooth(-1.88,-1.54,x)-.011*nares+.0026*nare_rims
                  +.018*root-.0033*lip_flute)
    y=(ry+detail)*s
    z=zc+(np.where(c>=0,top,bottom)+detail)*c
    return np.stack(np.broadcast_arrays(x,y,z),axis=-1)


def material(name, color, roughness, coat=.18, subsurface=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color,1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Coat Weight"].default_value = coat
    shader.inputs["Coat Roughness"].default_value = .27
    shader.inputs["Subsurface Weight"].default_value = subsurface
    shader.inputs["Subsurface Radius"].default_value = (1.0,.48,.32)
    shader.inputs["Subsurface Scale"].default_value = .005
    return mat


def color_material(name, roughness, coat, subsurface=0):
    mat = material(name, (1,1,1), roughness, coat, subsurface)
    node = mat.node_tree.nodes.new("ShaderNodeVertexColor")
    node.layer_name = "Pigment"
    mat.node_tree.links.new(node.outputs["Color"], mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    return mat


def mesh_object(name, points, faces, mat, colors=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(pose(points).tolist(), [], faces)
    mesh.update()
    # Keep studio and runtime exports on the same authored topology.
    if mesh.validate(verbose=False):
        raise RuntimeError(f"Invalid topology in {name}")
    obj = bpy.data.objects.new(name, mesh)
    asset.objects.link(obj)
    obj.data.materials.append(mat)
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), dtype=bool))
    if colors is not None:
        layer = mesh.color_attributes.new(name="Pigment", type="FLOAT_COLOR", domain="POINT")
        layer.data.foreach_set("color", np.asarray(colors,dtype=np.float32).ravel())
    return obj


def create_body():
    mat=material("Skin • "+TITLE,(1,1,1),.36,.13,.09)
    shader=mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Specular IOR Level"].default_value=.31
    albedo,normal_image,rough=generate_skin(VARIETY,lambda u:spline(PROFILE,u),
                                          skin_scales,gill_mask,nare_field,args.texture_width)
    def texture_node(image,x,y):
        node=mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image=image
        node.location=(x,y)
        return node

    albedo_tex=texture_node(albedo,-680,410)
    normal_tex=texture_node(normal_image,-680,100)
    surface_tex=texture_node(rough,-680,-230)
    normal=mat.node_tree.nodes.new("ShaderNodeNormalMap")
    normal.location=(-315,100)
    normal.inputs["Strength"].default_value=.85
    links=mat.node_tree.links
    links.new(albedo_tex.outputs["Color"],shader.inputs["Base Color"])
    links.new(normal_tex.outputs["Color"],normal.inputs["Color"])
    links.new(normal.outputs["Normal"],shader.inputs["Normal"])
    separate=mat.node_tree.nodes.new("ShaderNodeSeparateColor")
    separate.location=(-315,-230)
    links.new(surface_tex.outputs["Color"],separate.inputs[0])
    links.new(separate.outputs["Green"],shader.inputs["Roughness"])
    links.new(separate.outputs["Blue"],shader.inputs["Metallic"])
    # Denser samples resolve shallow scale relief without adding detached scale shells.
    rings, sides = 613, 302
    u = np.linspace(0,1,rings)[:,None]
    theta = np.linspace(-np.pi,np.pi,sides,endpoint=False)[None,:]
    points = body_surface(u,theta).reshape(-1,3).tolist()
    points.extend([[-2.70,0,-.177],[2.31,0,.072]])
    faces = []
    for i in range(rings-1):
        for j in range(sides):
            a,b = i*sides+j, i*sides+(j+1)%sides
            faces.append((a,a+sides,b+sides,b))
    for j in range(sides):
        n = (j+1)%sides
        last = (rings-1)*sides
        faces.extend([(j,n,rings*sides),(last+n,last+j,rings*sides+1)])
    obj = mesh_object("Body · scales, opercula and mouth",points,faces,mat)
    uv = obj.data.uv_layers.new(name="Skin UV")
    corners = np.arange((rings-1)*sides)
    t = (corners%sides)/sides
    q = (corners//sides)/(rings-1)
    quad = np.stack([np.stack([q,t],axis=1),np.stack([q+1/(rings-1),t],axis=1),
                     np.stack([q+1/(rings-1),t+1/sides],axis=1),np.stack([q,t+1/sides],axis=1)],axis=1)
    cap = np.zeros((sides,2,3,2), dtype=np.float32)
    n = np.arange(sides)/sides
    cap[:,0,:,1] = np.stack([n,n+1/sides,n+.5/sides],axis=1)
    cap[:,1,:,1] = np.stack([n+1/sides,n,n+.5/sides],axis=1)
    cap[:,1,:,0] = 1
    uv.uv.foreach_set("vector", np.concatenate([quad.reshape(-1,2),cap.reshape(-1,2)]).astype(np.float32).ravel())


def fin(name, roots, edge, normal, rays, thickness, warmth=.10):
    """Loft a cambered two-sided fin over its ray trajectories and close its perimeter."""
    mat = fin_material
    roots,edge,normal = map(np.asarray,(roots,edge,normal))
    n,m = rays*12+1,55
    along = np.linspace(0,1,n)[:,None]
    span = np.linspace(0,1,m)[None,:]
    root = spline(roots,along[:,0])
    rim = spline(edge,along[:,0])
    ridge_phase = along*(rays-1)
    wiggle = .032*np.sin(12*along+2)
    ridge_phase = ridge_phase + .17*np.sin(6*span+9*along)*span
    spread = .22*smooth(.44,.94,span)
    ridge = lambda shift: np.exp(-((np.sin(np.pi*(ridge_phase+shift)))/.31)**2)
    ribs = np.maximum(ridge(spread),ridge(-spread)*smooth(.36,.61,span))
    # Offset the joints of adjacent rays and fade segmentation at the soft leading edge.
    segments = .5+.5*np.cos(2*np.pi*(span*18+.38*np.sin(17*along)+.20*np.sin(21*span)))
    joint = (.32+.68*smooth(.15,.75,segments))*smooth(.13,.28,span)
    trailing = np.cos(2*np.pi*(rays-1)*along)*smooth(.68,1,span)
    mid = root[:,None,:]*(1-span[...,None])+rim[:,None,:]*span[...,None]
    camber = np.sin(np.pi*span)*(.060+wiggle)*np.sin(np.pi*along)
    mid += (camber+.009*np.sin(16*along+4*span)*span**2
            +.004*trailing)[...,None]*normal
    bulk = (.00072+thickness*(1-span)**1.9
            +(.004+.0044*ribs*(1-.26*joint))*np.sin(np.pi*(.08+.92*span)))
    bulk *= (.24+.76*np.sin(np.pi*along)**.5)
    points = np.concatenate([(mid+bulk[...,None]*normal).reshape(-1,3),
                             (mid-bulk[...,None]*normal).reshape(-1,3)])
    faces = []
    for i in range(n-1):
        for j in range(m-1):
            a,b = i*m+j,(i+1)*m+j
            faces.append((a,b,b+1,a+1))
            faces.append(tuple(p+n*m for p in (a,a+1,b+1,b)))
    edges = [*range(m),*(i*m+m-1 for i in range(1,n)),
             *range(n*m-2,(n-1)*m-1,-1),*(i*m for i in range(n-2,0,-1))]
    for a,b in zip(edges,edges[1:]+edges[:1]):
        faces.append((a,b,b+n*m,a+n*m))
    root_flush = warmth*(1-span)**3
    fiber = np.sin(139*along+12*span)*np.sin(87*span-9*along)
    color = (.60+.23*ribs-.17*span+.028*fiber-.058*ribs*joint)[...,None]*np.array([.78,.79,.72])
    color += root_flush[...,None]*np.array([.23,-.33,-.38])
    color += (span**2)[...,None]*np.array([.087,.117,.128])
    vessels = np.exp(-((np.sin(np.pi*(along*5.4+.22*np.sin(8*span))))/.085)**2)*(1-smooth(.22,.60,span))
    color += vessels[...,None]*np.array([.037,-.042,-.040])
    color = np.clip(fin_color(VARIETY,name,along,span,color),0,1)
    colors = np.concatenate([color,np.ones((n,m,1))],axis=-1).reshape(-1,4)
    fin_obj = mesh_object(name,points,faces,mat,np.tile(colors,(2,1)))
    # Mirrored fin layouts can reverse winding, so orient each closed shell by signed volume.
    orient_outward(fin_obj)


def orient_outward(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()


def create_fins():
    fin("Dorsal fin · 21 rays",
        [(-1.28,0,.54),(-1.0,0,.565),(-.54,0,.56),(-.04,0,.51),(.39,0,.455),(.86,0,.365),(1.02,0,.33)],
        [(-1.27,0,.546),(-.91,0,.927),(-.60,0,.800),(-.19,0,.726),(.27,0,.635),(.73,0,.579),(1.03,0,.337)],
        (0,1,0),21,.027)
    fin("Caudal fin · forked",
        [(2.02,0,z) for z in (.179,.151,.111,.070,.036,.002,-.036)],
        [(2.21,0,.195),(2.54,-.04,.427),(3.28,-.09,.606),(3.45,-.14,.609),
         (3.23,-.19,.337),(2.87,-.22,.092),(3.15,-.24,-.19),(3.37,-.27,-.487),
         (3.17,-.24,-.484),(2.53,-.09,-.227),(2.21,0,-.043)],
        (0,1,0),19,.029,.19)
    fin("Anal fin · 7 rays",
        [(.69,0,-.185),(.89,0,-.17),(1.16,0,-.12),(1.48,0,-.077)],
        [(.70,0,-.19),(1.03,.025,-.523),(1.25,.029,-.468),(1.49,0,-.079)],
        (0,1,0),7,.019)
    for side,label in [(1,"Left"),(-1,"Right")]:
        def mirror(points):
            return [(x,side*y,z) for x,y,z in points]

        # Small asymmetry opens both pectorals in the three-quarter and overhead views.
        sweep = .09 if side==1 else -.07
        fin(f"{label} pectoral fin",
            mirror([(-1.97,.311,-.211),(-1.83,.357,-.258),(-1.65,.359,-.280),(-1.48,.335,-.297)]),
            mirror([(-1.95,.321,-.220),(-1.77,.72,-.363),(-1.46,1.11+sweep,-.463),
                    (-1.12,1.15+sweep,-.481),(-.89,.92,-.415),(-1.00,.60,-.340),(-1.47,.343,-.304)]),
            (0,side*.28,.96),17,.037,.28)
        fin(f"{label} pelvic fin",
            mirror([(-.64,.261,-.325),(-.46,.260,-.343),(-.29,.230,-.340),(-.12,.189,-.322)]),
            mirror([(-.62,.274,-.337),(-.32,.49,-.522),(.10,.64,-.58),(.37,.53,-.50),(.31,.37,-.42),(-.10,.193,-.327)]),
            (0,side*.38,.93),9,.023,.16)


def eye(name, side):
    # Seat the iris on the outer curve of the skull. The radial surface includes the wet corneal dome.
    center = body_surface(np.asarray(axial_parameter(-2.43)),np.asarray(side*1.19),False)
    normal = Vector((-.26,side*.91,.31)).normalized()
    tangent = normal.cross(Vector((0,0,1))).normalized()
    vertical = normal.cross(tangent).normalized()
    sizes = [0,.19,.37,.47,.53,.57,.63,.70,.80,.89,.96,1.0]
    palette = [[.009,.011,.012],[.010,.012,.012],[.012,.014,.014],[.017,.018,.018],
               [.049,.038,.026],[.176,.114,.064],[.36,.255,.152],[.45,.355,.23],
               [.24,.208,.164],[.117,.116,.102],[.38,.352,.29],[.66,.591,.505]]
    count = 96
    theta = np.linspace(0,2*np.pi,count,endpoint=False)
    points, colors, faces = [], [], []
    points.append(center+np.asarray(normal)*.047)
    colors.append((*palette[0],1))
    for j,r in enumerate(sizes[1:],1):
        height = .049*(1-r**2)-.003+.010*np.exp(-((r-.94)/.06)**2)
        p = (center + np.asarray(normal)*height +
             r*(.101*np.cos(theta)[:,None]*np.asarray(tangent)+.088*np.sin(theta)[:,None]*np.asarray(vertical)))
        modulation = 1+(.21*np.sin(29*theta+2*r)+.10*np.sin(53*theta+4*r)+.11*np.sin(7*theta-3*r))*np.exp(-((r-.69)/.17)**2)
        points.extend(p)
        colors.extend(np.column_stack((modulation[:,None]*palette[j],np.ones(count))))
    for i in range(count):
        nxt = (i+1)%count
        faces.append((0,1+i,1+nxt))
        for r in range(len(sizes)-2):
            a,b = 1+r*count+i,1+r*count+nxt
            faces.append((a,a+count,b+count,b))
    points.append(center-np.asarray(normal)*.019)
    colors.append((.50,.45,.38,1))
    end = len(points)-1
    for i in range(count):
        faces.append((end,end-count+(i+1)%count,end-count+i))
    obj = mesh_object(name,points,faces,eye_material,colors)
    orient_outward(obj)


def barbel(name, path, radius):
    t = np.linspace(0,1,54)
    p = spline(np.array(path),t)
    tangent = np.gradient(p,axis=0)
    tangent /= np.linalg.norm(tangent,axis=1,keepdims=True)
    normal = np.cross(tangent,[0,0,1])
    normal /= np.linalg.norm(normal,axis=1,keepdims=True)
    binormal = np.cross(tangent,normal)
    angle = np.linspace(0,2*np.pi,14,endpoint=False)
    r = radius*(.065+.935*(1-t)**1.08)
    points = p[:,None,:]+r[:,None,None]*(np.cos(angle)[None,:,None]*normal[:,None,:] +
                                       np.sin(angle)[None,:,None]*binormal[:,None,:])
    k = len(angle)
    faces = [(i*k+j,i*k+(j+1)%k,(i+1)*k+(j+1)%k,(i+1)*k+j) for i in range(len(t)-1) for j in range(k)]
    faces += [tuple(range(k-1,-1,-1)),tuple(range((len(t)-1)*k,len(t)*k))]
    obj = mesh_object(name,points.reshape(-1,3),faces,barbel_material)
    orient_outward(obj)


fin_material = color_material("Fin membranes • segmented rays",.43,.12,.28)
eye_material = color_material("Eyes • radial iris under glossy cornea",.18,.42)
barbel_color = (.69,.47,.38) if VARIETY!="ogon" else (.68,.43,.14)
barbel_material = material("Barbels • fleshy surface",barbel_color,.38,.13,.14)
create_body()
create_fins()
for side,label in [(1,"Left"),(-1,"Right")]:
    eye(f"{label} eye",side)
    barbel(f"{label} lower barbel", [(-2.941,side*.155,-.174),(-2.896,side*.226,-.203),
                                    (-2.831,side*.287,-.238),(-2.721,side*.317,-.251),
                                    (-2.658,side*(.32 if side==1 else .30),-.242)],.022)
    barbel(f"{label} upper barbel", [(-2.962,side*.132,-.103),(-2.944,side*.193,-.115),
                                    (-2.899,side*.229,-.143),(-2.848,side*.240,-.146)],.017)


def bounds():
    points = [v.co for obj in asset.objects for v in obj.data.vertices]
    return np.asarray(points,dtype=np.float32).min(axis=0),np.asarray(points,dtype=np.float32).max(axis=0)


lo,hi = bounds()
scale = args.length_mm/1000/(hi[0]-lo[0])
# Authored mesh vertex coordinates are meters, with a centered asset origin and applied scale.
mid = (lo+hi)/2
for obj in asset.objects:
    data = obj.data.vertices
    xyz = np.empty(len(data)*3,dtype=np.float32)
    data.foreach_get("co",xyz)
    data.foreach_set("co",((xyz.reshape(-1,3)-mid)*scale).ravel())
    obj.data.update()

lo,hi = bounds()
dims = [float(round(float(v)*1000,3)) for v in hi-lo]
for obj in asset.objects:
    obj.data.calc_loop_triangles()
record = {"version":args.version,"variety":VARIETY,"texture_size":[args.texture_width,args.texture_width//2],"blender":bpy.app.version_string,"dimensions_mm":dims,
          "pieces":[{"name":obj.name,"vertices":len(obj.data.vertices),"triangles":len(obj.data.loop_triangles)}
                    for obj in asset.objects]}
(OUT/"evidence"/"geometry.json").write_text(json.dumps(record,indent=2)+"\n")
metadata = {
    "title":TITLE,
    "status":f"Version {args.version} · Ready for review",
    "facts":{
        "Pattern":DESCRIPTION,
        "Envelope":" × ".join(f"{v:.1f}" for v in dims)+" mm",
    },
    "note":"Use Overhead to compare markings. Open Head detail to see the nostrils, gill cover and barbels.",
    "prompt":"",
    "parts":[],
}
(OUT/"review"/"metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n")
for obj in asset.objects:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/"review"/"model.glb"),export_format="GLB",
                          use_selection=True,export_yup=True,export_attributes=False,
                          export_vertex_color="MATERIAL",export_all_vertex_colors=False,
                          export_materials="EXPORT")
for obj in asset.objects:
    obj.select_set(False)


def aim(obj,target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def link(name,data,location):
    obj = bpy.data.objects.new(name,data)
    studio.objects.link(obj)
    obj.location = location
    return obj


def area(name,location,energy,size,color,target=(0,0,0),size_y=None):
    data = bpy.data.lights.new(name,"AREA")
    factor = args.length_mm/700
    data.energy,data.size,data.color = energy*factor**2,size*factor,color
    if size_y:
        data.shape = "RECTANGLE"
        data.size_y = size_y*factor
    obj = link(name,data,Vector(location)*factor)
    aim(obj,Vector(target)*factor)


scene.world = bpy.data.worlds.new("Studio ambient")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.26,.37,.39,1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .36

floor_mesh = bpy.data.meshes.new("Matte backdrop")
floor_mesh.from_pydata([(-8,-8,0),(8,-8,0),(8,8,0),(-8,8,0)],[],[(0,1,2,3)])
floor = link("Matte backdrop",floor_mesh,(0,0,-.28*(args.length_mm/700)))
# A camera-only gradient keeps the backdrop even across the studio light cutoffs.
backdrop = bpy.data.materials.new("Deep teal studio")
backdrop.use_nodes = True
nodes, links = backdrop.node_tree.nodes, backdrop.node_tree.links
nodes.clear()
coordinates = nodes.new("ShaderNodeTexCoord")
distance = nodes.new("ShaderNodeVectorMath")
distance.operation = "LENGTH"
links.new(coordinates.outputs["Object"], distance.inputs[0])
gradient = nodes.new("ShaderNodeValToRGB")
gradient.color_ramp.interpolation = "EASE"
gradient.color_ramp.elements[0].color = (.036,.064,.072,1)
gradient.color_ramp.elements[1].color = (.008,.018,.022,1)
links.new(distance.outputs["Value"], gradient.inputs[0])
emission = nodes.new("ShaderNodeEmission")
links.new(gradient.outputs["Color"], emission.inputs["Color"])
surface = nodes.new("ShaderNodeOutputMaterial")
links.new(emission.outputs[0], surface.inputs["Surface"])
floor.data.materials.append(backdrop)
floor.visible_diffuse = floor.visible_glossy = floor.visible_transmission = floor.visible_shadow = False
area("Warm overhead softbox",(-.27,-.40,.65),15,.78,(1,.91,.82),size_y=.39)
area("Cool long rim",(.21,.41,.42),23,.77,(.72,.88,1),size_y=.20)
area("Head reflection",(-.63,.18,.23),6,.36,(.91,.97,1),(-.21,0,0))
area("Flank fill",(.19,-.57,.04),4,.43,(.89,1,1))
area("Belly fill",(-.31,.13,-.17),1.7,.32,(1,.90,.83))

camera = link("Camera",bpy.data.cameras.new("Studio orthographic"),(0,0,1))
camera.data.type = "ORTHO"
scene.camera = camera
scene.render.engine = "CYCLES"
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 5
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_percentage = args.preview_percent
scene.render.use_persistent_data = True

shots = [
    ("three-quarter",(-.45,-.93,.74),(0,0,-.01),.825,1440,935),
    ("overhead",(0,-.002,1.3),(0,0,0),.815,1370,820),
]
if VARIETY=="kohaku":
    shots.extend([
        ("profile",(-.05,.96,.12),(0,0,0),.817,1440,810),
        ("head-detail",(-.56,-.71,.30),(-.248,0,-.002),.310,1450,1040),
    ])
for index,(name,location,target,crop,width,height) in enumerate(shots):
    factor = args.length_mm/700
    camera.location = Vector(location)*factor
    aim(camera,Vector(target)*factor)
    camera.data.ortho_scale = crop*factor
    scene.render.resolution_x,scene.render.resolution_y = width,height
    scene.render.filepath = str(OUT/"preview"/(name+".png"))
    # Open the authored file with its principal studio composition ready to render.
    if index == 0:
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    area.spaces.active.region_3d.view_perspective = "CAMERA"
        bpy.context.preferences.filepaths.save_version = 0
        absolute_render_path = scene.render.filepath
        scene.render.filepath = "//preview/three-quarter.png"
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(VARIETY+".blend")),compress=True)
        scene.render.filepath = absolute_render_path
    if not args.skip_renders:
        bpy.ops.render.render(write_still=True)
