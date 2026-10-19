from panda3d.core import (
    CardMaker, TransparencyAttrib, Shader,
    LineSegs, LPoint3, SamplerState
)
import math
import random
import glob

ROCK_MODELS = sorted(glob.glob("assets/models/Rock*.glb"))
SPACESHIP_MODELS = sorted(glob.glob("assets/models/Spaceship*.glb"))
BACKGROUND_MODELS = ROCK_MODELS + SPACESHIP_MODELS

# Cache des shaders : chaque shader GLSL n'est compilé qu'une seule fois
_SHADER_CACHE = {}


def _load_cached(name, vertex, fragment):
    if name not in _SHADER_CACHE:
        _SHADER_CACHE[name] = Shader.load(
            Shader.SL_GLSL, vertex=vertex, fragment=fragment
        )
    return _SHADER_CACHE[name]


def load_sphere_shader():
    # Shader sphère : Fresnel + Phong + rim light pour un rendu volumétrique
    return _load_cached("sphere", "shaders/sphere.vert", "shaders/sphere.frag")


def load_glow_shader():
    # Shader halo : falloff gaussien rond (pas de carré visible)
    return _load_cached("glow", "shaders/glow.vert", "shaders/glow.frag")


def load_blackhole_shader():
    # Shader trou noir : Fresnel + disque d'accrétion animé
    return _load_cached("blackhole", "shaders/blackhole.vert", "shaders/blackhole.frag")




def create_starfield(render, loader, num_stars=250):
    """Champ de fond : asteroïdes et vaisseaux eparpillés au loin."""
    objs = []
    for i in range(num_stars):
        theta = random.uniform(0, math.pi * 2)
        phi = random.uniform(0, math.pi)
        r = random.uniform(300, 500)
        x = r * math.sin(phi) * math.cos(theta)
        y = r * math.sin(phi) * math.sin(theta)
        z = r * math.cos(phi)

        if not BACKGROUND_MODELS:
            break
        obj = loader.loadModel(random.choice(BACKGROUND_MODELS))
        obj.reparentTo(render)
        obj.setPos(x, y, z)
        obj.setScale(random.uniform(0.8, 2.5))
        obj.setLightOff()
        obj.setHpr(random.randint(0, 360), random.randint(0, 360), random.randint(0, 360))
        obj.setColorScale(1, 1, 1, 1)   # tu peux teinter (ex. 0.6,0.7,1 pour un bleu froid)
        objs.append(obj)
    return objs


def create_skybox(render, loader, texture_path="assets/milky_way.jpg"):
    # Tentative de skybox voie lactée — silencieuse si la texture est absente
    try:
        skybox = loader.loadModel("models/misc/sphere")
        skybox.reparentTo(render)
        skybox.setScale(800)
        skybox.setLightOff()
        skybox.setBin("background", 0)
        skybox.setDepthWrite(False)
        skybox.setTwoSided(True)

        tex = loader.loadTexture(texture_path)
        if tex:
            tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
            skybox.setTexture(tex, 1)
            skybox.setTexScale(1, 1, -1)
        else:
            # Pas de texture : fond sombre uni
            skybox.setColor(0.004, 0.006, 0.018, 1)
            skybox.setTexture(tex)
            skybox.setColorScale(1.3, 1.3, 1.4, 1)  # léger boost de luminosité

        return skybox
    except Exception:
        return None


def create_glow(render, loader, parent_np, color, scale_factor=2.5):
    # Halo gaussien rond via shader GLSL (pas de carré billboard visible)
    glow_shader = load_glow_shader()

    cm = CardMaker("glow")
    cm.setFrame(-1, 1, -1, 1)
    cm.setUvRange((0, 0), (1, 1))
    glow_np = render.attachNewNode(cm.generate())
    glow_np.reparentTo(parent_np)
    glow_np.setPos(0, 0, 0)

    r, g, b, _ = color
    glow_np.setShader(glow_shader)
    glow_np.setShaderInput("glow_color", r, g, b, 0.45)
    glow_np.setTransparency(TransparencyAttrib.MAlpha)
    glow_np.setLightOff()
    glow_np.setTwoSided(True)
    glow_np.setScale(scale_factor)
    glow_np.setBillboardPointEye()
    glow_np.setBin("transparent", 10)
    glow_np.setDepthWrite(False)

    return glow_np


def create_orbital_ring(render, parent_np, color, radius=1.6):
    # Anneau orbital principal + second anneau incliné pour l'effet holographique
    r, g, b, _ = color
    segments   = 80

    def make_ring(r_main, r_val, g_val, b_val, alpha, thickness, tilt=0):
        ls = LineSegs()
        ls.setColor(r_val, g_val, b_val, alpha)
        ls.setThickness(thickness)
        for i in range(segments + 1):
            angle = (i / segments) * math.pi * 2
            x = math.cos(angle) * r_main
            z = math.sin(angle) * r_main
            if i == 0:
                ls.moveTo(x, 0, z)
            else:
                ls.drawTo(x, 0, z)
        np = render.attachNewNode(ls.create())
        np.reparentTo(parent_np)
        np.setPos(0, 0, 0)
        if tilt:
            np.setHpr(0, tilt, 0)
        np.setLightOff()
        return np

    container = render.attachNewNode("ring_container")
    make_ring(radius,       r,     g,     b,     1.0, 2.0)
    make_ring(radius * 1.3, r*0.6, g*0.6, b,     0.5, 1.0, tilt=45)
    container.reparentTo(parent_np)

    return container


def create_accretion_disk(render, loader, center, time_input=0.0):
    # Trou noir : sphère avec shader animé (Fresnel + disque d'accrétion)
    bh_shader = load_blackhole_shader()

    bh = loader.loadModel("models/misc/sphere")
    bh.reparentTo(render)
    bh.setPos(center)
    bh.setScale(2.8)
    bh.setLightOff()
    bh.setTransparency(TransparencyAttrib.MAlpha)
    bh.setShader(bh_shader)
    bh.setShaderInput("time", time_input)
    bh.setBin("transparent", 1)
    bh.setDepthWrite(False)

    # Cœur noir opaque (masque le centre)
    core = loader.loadModel("models/misc/sphere")
    core.reparentTo(render)
    core.setPos(center)
    core.setScale(2.0)
    core.setColor(0.0, 0.0, 0.0, 1.0)
    core.setLightOff()

    return bh, core

def create_nebula(render, loader, textures, num=14):
    """Grands voiles de gaz colores en arriere-plan, superposes a la skybox."""
    nebulas = []
    import random as rnd
    for i in range(num):
        tex_path = rnd.choice(textures)
        cm = CardMaker("nebula")
        cm.setFrame(-1, 1, -1, 1)
        cm.setUvRange((0, 0), (1, 1))
        np = render.attachNewNode(cm.generate())

        theta = rnd.uniform(0, math.pi * 2)
        phi = rnd.uniform(-0.6, 0.6)
        dist = rnd.uniform(500, 700)
        np.setPos(dist * math.cos(phi) * math.cos(theta),
                  dist * math.cos(phi) * math.sin(theta),
                  dist * math.sin(phi))
        np.lookAt(0, 0, 0)

        tint = rnd.choice([
            (0.9, 0.3, 0.9),   # violet
            (0.3, 0.4, 1.0),   # bleu
            (1.0, 0.4, 0.7),   # rose
            (0.4, 0.9, 0.8),   # turquoise
        ])
        np.setColorScale(tint[0], tint[1], tint[2], 1)
        np.setTransparency(TransparencyAttrib.MAlpha)
        np.setAlphaScale(rnd.uniform(0.25, 0.5))
        np.setScale(rnd.uniform(150, 300))
        np.setLightOff()
        np.setBin("background", 1)      # derriere tout, devant la skybox
        np.setDepthWrite(False)
        np.setDepthTest(False)
        np.setBillboardPointEye()

        tex = loader.loadTexture(tex_path)
        tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        np.setTexture(tex)
        nebulas.append(np)
    return nebulas