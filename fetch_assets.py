"""Telecharge les textures spatiales libres de droits (CC BY 4.0 / NASA).
Usage : python fetch_assets.py
"""
import os
import urllib.request

BASE = "https://www.solarsystemscope.com/textures/download"
NASA_STARMAP = (
    "https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004856/"
    "starmap_random_2020_4k_print.jpg"
)

FILES = {
    # Skybox : voie lactee pour le fond de scene
    "milky_way.jpg": f"{BASE}/2k_stars_milky_way.jpg",
    # Planetes pour les dossiers
    "mercury.jpg": f"{BASE}/2k_mercury.jpg",
    "venus.jpg": f"{BASE}/2k_venus_atmosphere.jpg",
    "earth.jpg": f"{BASE}/2k_earth_daymap.jpg",
    "mars.jpg": f"{BASE}/2k_mars.jpg",
    "jupiter.jpg": f"{BASE}/2k_jupiter.jpg",
    "saturn.jpg": f"{BASE}/2k_saturn.jpg",
    "saturn_ring.png": f"{BASE}/2k_saturn_ring_alpha.png",
    "uranus.jpg": f"{BASE}/2k_uranus.jpg",
    "neptune.jpg": f"{BASE}/2k_neptune.jpg",
    "moon.jpg": f"{BASE}/2k_moon.jpg",
    "sun.jpg": f"{BASE}/2k_sun.jpg",
    # Carte stellaire NASA (domaine public) en alternative skybox
    "nasa_starmap.jpg": NASA_STARMAP,
}

os.makedirs("assets", exist_ok=True)

for name, url in FILES.items():
    dest = os.path.join("assets", name)
    if os.path.exists(dest):
        print(f"[ok] {name} deja present")
        continue
    print(f"[..] telechargement {name}")
    urllib.request.urlretrieve(url, dest)
    print(f"[ok] {name}")

print("Termine ! Toutes les textures sont dans assets/")