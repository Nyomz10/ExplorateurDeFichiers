from panda3d.core import (
    CardMaker, TransparencyAttrib, Shader, ShaderAttrib,
    LineSegs, LPoint3
)
import math
import random


def load_sphere_shader():
    # Shader GLSL pour les sphères : Fresnel + Phong + rim light
    return Shader.load(
        Shader.SL_GLSL,
        vertex="shaders/sphere.vert",
        fragment="shaders/sphere.frag"
    )


def load_glow_shader():
    # Shader GLSL pour les halos : falloff gaussien rond
    return Shader.load(
        Shader.SL_GLSL,
        vertex="shaders/glow.vert",
        fragment="shaders/glow.frag"
    )


def load_blackhole_shader():
    # Shader GLSL pour le trou noir : Fresnel + disque d'accrétion animé
    return Shader.load(
        Shader.SL_GLSL,
        vertex="shaders/blackhole.vert",
        fragment="shaders/blackhole.frag"
    )


def create_starfield(render, loader, num_stars=1200):
    # Champ d'étoiles : petites sphères avec le shader sphère, sans les carrés billboard
    stars = []
    sphere_shader = load_sphere_shader()

    for i in range(num_stars):
        theta = random.uniform(0, math.pi * 2)
        phi = random.uniform(0, math.pi)
        r = random.uniform(300, 500)
        x = r * math.sin(phi) * math.cos(theta)
        y = r * math.sin(phi) * math.sin(theta)
        z = r * math.cos(phi)

        size = random.uniform(0.15, 0.6)
        brightness = random.uniform(0.5, 1.0)
        color = random.choice([
            (brightness, brightness, brightness, 1.0),
            (brightness * 0.7, brightness * 0.85, brightness, 1.0),
            (brightness, brightness * 0.95, brightness * 0.7, 1.0),
        ])

        star = loader.loadModel("models/misc/sphere")
        star.reparentTo(render)
        star.setPos(x, y, z)
        star.setScale(size)
        star.setLightOff()
        star.setShader(sphere_shader)
        star.setShaderInput("sphere_color", *color)
        star.setShaderInput("time", 0.0)
        stars.append(star)

    return stars


def create_glow(render, loader, parent_np, color, scale_factor=2.5):
    # Halo gaussien rond via shader GLSL (plus de carré visible)
    glow_shader = load_glow_shader()

    cm = CardMaker("glow")
    cm.setFrame(-1, 1, -1, 1)
    cm.setUvRange((0, 0), (1, 1))
    glow_np = render.attachNewNode(cm.generate())
    glow_np.reparentTo(parent_np)
    glow_np.setPos(0, 0, 0)

    r, g, b, _ = color
    glow_np.setShader(glow_shader)
    glow_np.setShaderInput("glow_color", r, g, b, 0.55)
    glow_np.setTransparency(TransparencyAttrib.MAlpha)
    glow_np.setLightOff()
    glow_np.setTwoSided(True)
    glow_np.setScale(scale_factor)
    glow_np.setBillboardPointEye()
    glow_np.setBin("transparent", 10)
    glow_np.setDepthWrite(False)

    return glow_np


def create_orbital_ring(render, parent_np, color, radius=1.6):
    # Anneau orbital lumineux dessiné avec LineSegs
    ls = LineSegs()
    r, g, b, _ = color
    ls.setColor(r, g, b, 1.0)
    ls.setThickness(2.0)

    segments = 80
    for i in range(segments + 1):
        angle = (i / segments) * math.pi * 2
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius
        if i == 0:
            ls.moveTo(x, 0, z)
        else:
            ls.drawTo(x, 0, z)

    ring_np = render.attachNewNode(ls.create())
    ring_np.reparentTo(parent_np)
    ring_np.setPos(0, 0, 0)
    ring_np.setLightOff()

    # Second anneau incliné pour l'effet holographique
    ls2 = LineSegs()
    ls2.setColor(r * 0.6, g * 0.6, b, 0.5)
    ls2.setThickness(1.0)
    for i in range(segments + 1):
        angle = (i / segments) * math.pi * 2
        x = math.cos(angle) * radius * 1.3
        z = math.sin(angle) * radius * 1.3
        if i == 0:
            ls2.moveTo(x, 0, z)
        else:
            ls2.drawTo(x, 0, z)

    ring2_np = render.attachNewNode(ls2.create())
    ring2_np.reparentTo(parent_np)
    ring2_np.setPos(0, 0, 0)
    ring2_np.setHpr(0, 45, 0)
    ring2_np.setLightOff()

    container = render.attachNewNode("ring_container")
    ring_np.reparentTo(container)
    ring2_np.reparentTo(container)
    container.reparentTo(parent_np)

    return container


def create_accretion_disk(render, loader, center, time_input=0.0):
    # Trou noir avec shader GLSL : Fresnel + disque d'accrétion animé
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

    # Sphère noire centrale opaque (cœur du trou noir)
    core = loader.loadModel("models/misc/sphere")
    core.reparentTo(render)
    core.setPos(center)
    core.setScale(2.0)
    core.setColor(0.0, 0.0, 0.0, 1.0)
    core.setLightOff()

    return bh, core