from pathlib import Path
import os
import string

def get_root_path():
    # "Ce PC" n'est pas un vrai chemin : marqueur spécial
    return "CE_PC"

def _get_special_folders():
    # Dossiers rapides affichés par Windows dans "Ce PC"
    home = Path.home()
    candidates = [
        ("Bureau", home / "Desktop"),
        ("Documents", home / "Documents"),
        ("Images", home / "Pictures"),
        ("Musique", home / "Music"),
        ("Téléchargements", home / "Downloads"),
        ("Vidéos", home / "Videos"),
        ("Objets 3D", home / "3D Objects"),
    ]
    folders = []
    for display_name, path in candidates:
        if path.exists():
            folders.append({"name": display_name, "path": path, "type": "folder"})
    return folders

def _get_drives():
    drives = []
    for letter in string.ascii_uppercase:
        drive_path = Path(f"{letter}:\\")
        if drive_path.exists():
            drives.append({"name": f"{letter}:", "path": drive_path, "type": "folder"})
    return drives

def list_dir(path):
    # Racine spéciale : dossiers rapides + disques, comme la vraie vue "Ce PC"
    if path == "CE_PC":
        return _get_special_folders() + _get_drives()

    # Dossier classique : lecture normale
    entries = []
    try:
        for item in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            entries.append({
                "name": item.name,
                "path": item,
                "type": "folder" if item.is_dir() else "file",
            })
    except (PermissionError, OSError) as e:
        print(f"Accès refusé à {path} : {e}")
    return entries

def open_file(path):
    try:
        os.startfile(str(path))
    except OSError as e:
        print(f"Impossible d'ouvrir {path} : {e}")
        