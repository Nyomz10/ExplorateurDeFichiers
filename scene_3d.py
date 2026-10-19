from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    PointLight, AmbientLight, DirectionalLight, LColor, TextNode, LPoint3,
    ClockObject, TransparencyAttrib, SamplerState,
)
from direct.gui.OnscreenText import OnscreenText
import math
import cv2
import mediapipe as mp
import file_system
import gestures
import shaders
import random
import random
import glob
import os


def _collect_models(pattern):
    """Liste les .glb d'un motif, triée, avec repli sur le modele de base."""
    files = sorted(glob.glob(f"assets/models/{pattern}"))
    return files if files else []

FOLDER_MODELS = _collect_models("Planet*.glb")      # dossiers
FILE_MODELS = _collect_models("Rock*.glb")          # fichiers
MORE_MODELS = _collect_models("Spaceship*.glb")     # indicateur pagination

ORBIT_RADIUS_BY_DEPTH = [13, 6, 3]
MAX_ITEMS_PER_LEVEL   = 15
DOUBLE_FIST_WINDOW    = 0.7
ROTATE_SENSITIVITY    = 300
ZOOM_SENSITIVITY      = 50
MIN_CAM_DIST          = 6
MAX_CAM_DIST          = 60
GESTURE_COOLDOWN      = 2
PREVIOUS_LEVEL_ALPHA  = 0.15
PAGE_SIZE             = MAX_ITEMS_PER_LEVEL - 1
FLIP_THRESHOLD        = 0.01

FILE_TYPE_COLORS = {
    ".png":  (0.8, 0.3, 0.9, 1), ".jpg":  (0.8, 0.3, 0.9, 1),
    ".jpeg": (0.8, 0.3, 0.9, 1), ".gif":  (0.8, 0.3, 0.9, 1),
    ".bmp":  (0.8, 0.3, 0.9, 1), ".svg":  (0.8, 0.3, 0.9, 1),
    ".webp": (0.8, 0.3, 0.9, 1),
    ".mp4":  (0.9, 0.25, 0.25, 1), ".mkv": (0.9, 0.25, 0.25, 1),
    ".avi":  (0.9, 0.25, 0.25, 1), ".mov": (0.9, 0.25, 0.25, 1),
    ".webm": (0.9, 0.25, 0.25, 1),
    ".mp3":  (0.3, 0.9, 0.4, 1), ".wav":  (0.3, 0.9, 0.4, 1),
    ".flac": (0.3, 0.9, 0.4, 1), ".ogg":  (0.3, 0.9, 0.4, 1),
    ".m4a":  (0.3, 0.9, 0.4, 1),
    ".pdf":  (1.0, 0.85, 0.3, 1), ".doc":  (1.0, 0.85, 0.3, 1),
    ".docx": (1.0, 0.85, 0.3, 1), ".txt":  (1.0, 0.85, 0.3, 1),
    ".md":   (1.0, 0.85, 0.3, 1), ".rtf":  (1.0, 0.85, 0.3, 1),
    ".xls":  (1.0, 0.6, 0.2, 1), ".xlsx": (1.0, 0.6, 0.2, 1),
    ".csv":  (1.0, 0.6, 0.2, 1), ".ppt":  (1.0, 0.6, 0.2, 1),
    ".pptx": (1.0, 0.6, 0.2, 1),
    ".py":   (0.3, 0.9, 0.9, 1), ".js":   (0.3, 0.9, 0.9, 1),
    ".html": (0.3, 0.9, 0.9, 1), ".css":  (0.3, 0.9, 0.9, 1),
    ".json": (0.3, 0.9, 0.9, 1), ".cpp":  (0.3, 0.9, 0.9, 1),
    ".java": (0.3, 0.9, 0.9, 1),
    ".zip":  (0.5, 0.5, 0.7, 1), ".rar":  (0.5, 0.5, 0.7, 1),
    ".7z":   (0.5, 0.5, 0.7, 1),
}
DEFAULT_FILE_COLOR = (0.8, 0.8, 0.8, 1)


def get_file_color(name):
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return FILE_TYPE_COLORS.get(ext, DEFAULT_FILE_COLOR)


class GestureDesktopApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.setBackgroundColor(0.004, 0.006, 0.018, 1)
        self.disableMouse()

        self.cam_h    = 0
        self.cam_p    = 0
        self.cam_dist = 40
        self.current_center = LPoint3(0, 0, 0)

        self.nav_stack      = []
        self.selected_index = -1
        self.current_nodes  = []
        self.orbital_ring   = None

        # Infos du niveau affiché pour la pagination
        self.level_full_entries = []
        self.level_center   = LPoint3(0, 0, 0)
        self.level_is_root  = True
        self.level_depth    = 0
        self.level_label    = ""
        self.level_offset   = 0

        self._setup_lights()

        self.breadcrumb = OnscreenText(
            text="Ce PC", pos=(0, 0.9), scale=0.07,
            fg=(0.8, 1.0, 1.0, 1), align=TextNode.ACenter
        )
        self.gesture_label = OnscreenText(
            text="", pos=(0, 0.8), scale=0.05,
            fg=(1.0, 1.0, 0.4, 1), align=TextNode.ACenter
        )

        root_entries = file_system.list_dir(file_system.get_root_path())
        self._build_level(root_entries, center=LPoint3(0, 0, 0),
                          is_root=True, depth=0, label="Ce PC")
        self._update_camera()

        # Champ d'étoiles de fond (petites sphères avec shader)
        self.starfield = shaders.create_starfield(self.render, self.loader)

        # Skybox voie lactée
        self.skybox = shaders.create_skybox(self.render, self.loader)
        self.nebulas = shaders.create_nebula(self.render, self.loader, [
            "assets/jupiter.jpg", "assets/saturn.jpg",
            "assets/neptune.jpg", "assets/venus.jpg",
        ])

        for neb in getattr(self, "nebulas", []):
            neb.setPos(self.camera.getPos(self.render))

        # Contrôles clavier de secours
        for key, axis, delta in [
            ("arrow_left",  "h", -3), ("arrow_right", "h",  3),
            ("arrow_up",    "p",  3), ("arrow_down",  "p", -3),
        ]:
            self.accept(key,             self._rotate, [axis, delta])
            self.accept(key + "-repeat", self._rotate, [axis, delta])

        self.accept("tab",       self._next_star)
        self.accept("enter",     self._open_selected)
        self.accept("backspace", self._go_back)
        self.accept("escape",    self.userExit)

        OnscreenText(
            text="pincement+déplacer=tourner | 2 mains pincées=zoom | "
                 "index+majeur=sélectionner | double poing=ouvrir | "
                 "retourner main droite ouverte=retour",
            pos=(0, -0.90), scale=0.04,
            fg=(0.3, 0.7, 1.0, 1), align=TextNode.ACenter
        )
        OnscreenText(
            text="Clavier : flèches orbiter | Tab sélectionner | "
                 "Entrée ouvrir | Retour arrière | Échap quitter",
            pos=(0, -0.97), scale=0.04,
            fg=(0.3, 0.7, 1.0, 1), align=TextNode.ACenter
        )

        self._setup_hand_tracking()
        self._anim_time = 0.0
        self.taskMgr.add(self._animate_task,        "animate")
        self.taskMgr.add(self._gesture_update_task, "gesture_update")

    # ---------- Suivi des mains ----------

    def _setup_hand_tracking(self):
        self.cap      = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.mp_hands = mp.solutions.hands
        self.hands    = self.mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6
        )
        self.prev_single_pinch_pos  = None
        self.prev_two_hand_dist     = None
        self.was_pointing           = False
        self.was_fist               = False
        self.last_action_time       = 0.0
        self.last_fist_press_time   = None
        self.fist_orientation_start = None
        # Un seul handler pour window-event (ratio d'aspect)
        self.accept("window-event", self._on_window_event)

    def _on_window_event(self, window):
        # Adapte le ratio quand la fenêtre est redimensionnée
        wp = window.getProperties()
        if wp.getXSize() > 0 and wp.getYSize() > 0:
            self.camLens.setAspectRatio(wp.getXSize() / wp.getYSize())

    def _gesture_update_task(self, task):
        ok, frame = self.cap.read()
        if not ok:
            return task.cont

        frame  = cv2.flip(frame, 1)
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        now        = ClockObject.getGlobalClock().getFrameTime()
        label_text = ""

        hands_data = []
        if result.multi_hand_landmarks and result.multi_handedness:
            for lm, handedness in zip(result.multi_hand_landmarks,
                                      result.multi_handedness):
                hands_data.append({
                    "landmarks": lm,
                    "label":     gestures.get_hand_label(handedness),
                    "pinching":  gestures.is_pinching(lm),
                    "pointing":  gestures.is_index_pointing(lm),
                })

        right_hand     = next((h for h in hands_data if h["label"] == "Right"), None)
        pinching_hands = [h for h in hands_data if h["pinching"]]

        # --- Zoom à deux mains pincées ---
        if len(pinching_hands) == 2:
            a = gestures.get_wrist_pos(pinching_hands[0]["landmarks"])
            b = gestures.get_wrist_pos(pinching_hands[1]["landmarks"])
            dist = math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)
            if self.prev_two_hand_dist is not None:
                delta         = dist - self.prev_two_hand_dist
                self.cam_dist -= delta * ZOOM_SENSITIVITY
                adapted_min   = max(1.5, MIN_CAM_DIST - len(self.nav_stack)*1.5)
                self.cam_dist = max(adapted_min, min(MAX_CAM_DIST, self.cam_dist))
                self._update_camera()
            self.prev_two_hand_dist    = dist
            self.prev_single_pinch_pos = None
            label_text = "ZOOM"

        # --- Rotation avec une seule main pincée ---
        elif len(pinching_hands) == 1:
            pos = gestures.get_wrist_pos(pinching_hands[0]["landmarks"])
            if self.prev_single_pinch_pos is not None:
                dx = pos[0] - self.prev_single_pinch_pos[0]
                dy = pos[1] - self.prev_single_pinch_pos[1]
                self.cam_h -= dx * ROTATE_SENSITIVITY
                self.cam_p  = max(-89, min(89, self.cam_p + dy*ROTATE_SENSITIVITY))
                self._update_camera()
            self.prev_single_pinch_pos = pos
            self.prev_two_hand_dist    = None
            label_text = "ROTATION"
        else:
            self.prev_single_pinch_pos = None
            self.prev_two_hand_dist    = None

        # --- Sélection : index + majeur levés ---
        pointing_now = any(gestures.is_two_fingers(h["landmarks"]) for h in hands_data)
        if pointing_now and not self.was_pointing and \
                (now - self.last_action_time) > GESTURE_COOLDOWN:
            self._select_nearest_to_camera()
            self.last_action_time = now
            label_text = "SÉLECTION"
        self.was_pointing = pointing_now

        # --- Ouverture : double poing ---
        fist_now = any(
            gestures.is_fist(h["landmarks"]) and not h["pinching"]
            for h in hands_data
        )
        if fist_now and not self.was_fist:
            if self.last_fist_press_time is not None and \
                    (now - self.last_fist_press_time) < DOUBLE_FIST_WINDOW:
                self._open_selected()
                self.last_action_time     = now
                self.last_fist_press_time = None
                label_text = "OUVERTURE"
            else:
                self.last_fist_press_time = now
        self.was_fist = fist_now

        # --- Retour arrière : main droite ouverte retournée ---
        right_open = (
            right_hand
            if right_hand is not None
            and gestures.is_open_palm(right_hand["landmarks"])
            and not right_hand["pinching"]
            and len(pinching_hands) == 0
            else None
        )
        if right_open is not None:
            orientation = gestures.get_hand_orientation(right_open["landmarks"])
            if self.fist_orientation_start is None:
                if abs(orientation) > FLIP_THRESHOLD:
                    self.fist_orientation_start = orientation
            else:
                flipped = (orientation > 0) != (self.fist_orientation_start > 0)
                if flipped and abs(orientation) > FLIP_THRESHOLD and \
                        (now - self.last_action_time) > GESTURE_COOLDOWN:
                    self._go_back()
                    self.last_action_time       = now
                    self.fist_orientation_start = None
                    label_text = "RETOUR"
        else:
            self.fist_orientation_start = None

        self.gesture_label.setText(label_text)
        return task.cont

    # ---------- Caméra ----------

    def _rotate(self, axis, delta):
        if axis == "h":
            self.cam_h += delta
        else:
            self.cam_p = max(-89, min(89, self.cam_p + delta))
        self._update_camera()

    def _update_camera(self):
        rad_h = math.radians(self.cam_h)
        rad_p = math.radians(self.cam_p)
        x =  self.cam_dist * math.cos(rad_p) * math.sin(rad_h)
        y = -self.cam_dist * math.cos(rad_p) * math.cos(rad_h)
        z =  self.cam_dist * math.sin(rad_p)
        self.camera.setPos(self.current_center + LPoint3(x, y, z))
        self.camera.lookAt(self.current_center)
        # La skybox suit la caméra pour rester en fond
        if hasattr(self, "skybox") and self.skybox is not None:
            self.skybox.setPos(self.camera.getPos(self.render))

    def _animate_camera_to(self, new_center, new_dist, duration=1.0):
        self._transition = {
            "t": 0.0, "duration": duration,
            "start_center": LPoint3(self.current_center),
            "end_center":   LPoint3(new_center),
            "start_dist":   self.cam_dist,
            "end_dist":     new_dist,
        }
        self.taskMgr.add(self._transition_task, "cam_transition")

    def _transition_task(self, task):
        tr    = self._transition
        tr["t"] += ClockObject.getGlobalClock().getDt()
        ratio = min(tr["t"] / tr["duration"], 1.0)
        ease  = 1 - (1 - ratio) ** 2
        self.current_center = tr["start_center"] + \
            (tr["end_center"] - tr["start_center"]) * ease
        self.cam_dist = tr["start_dist"] + \
            (tr["end_dist"] - tr["start_dist"]) * ease
        self._update_camera()
        return task.done if ratio >= 1.0 else task.cont

    # ---------- Sélection ----------

    def _next_star(self):
        if not self.current_nodes:
            return
        if self.selected_index >= 0:
            self._set_highlight(self.current_nodes[self.selected_index], False)
        self.selected_index = (self.selected_index + 1) % len(self.current_nodes)
        self._set_highlight(self.current_nodes[self.selected_index], True)

    def _select_nearest_to_camera(self):
        if not self.current_nodes:
            return
        cam_pos = self.camera.getPos(self.render)
        nearest = min(
            range(len(self.current_nodes)),
            key=lambda i: (
                self.current_nodes[i]["node"].getPos(self.render) - cam_pos
            ).length()
        )
        if self.selected_index >= 0:
            self._set_highlight(self.current_nodes[self.selected_index], False)
        self.selected_index = nearest
        self._set_highlight(self.current_nodes[self.selected_index], True)

    def _set_highlight(self, entry, active):
        node = entry["node"]
        if active:
            node.setColor(0.0, 1.0, 1.0, 1)
            node.setScale(entry["base_scale"] * 1.4)
            if self.orbital_ring is not None:
                self.orbital_ring.removeNode()
            self.orbital_ring = shaders.create_orbital_ring(
                self.render, node, (0.0, 1.0, 1.0, 1),
                radius=entry["base_scale"] * 2.2
            )
        else:
            node.setColor(*entry["color"])
            node.setScale(entry["base_scale"])
            if self.orbital_ring is not None:
                self.orbital_ring.removeNode()
                self.orbital_ring = None

    # ---------- Ouverture / retour ----------

    def _open_selected(self):
        if self.selected_index < 0 or not self.current_nodes:
            return
        entry = self.current_nodes[self.selected_index]

        # Pagination : charge la page suivante
        if entry["type"] == "more":
            for n in self.current_nodes:
                n["node"].removeNode()
            self._build_level(
                self.level_full_entries, center=self.level_center,
                is_root=self.level_is_root, depth=self.level_depth,
                label=self.level_label,
                offset=self.level_offset + PAGE_SIZE
            )
            return

        # Fichier : ouverture Windows
        if entry["type"] == "file":
            file_system.open_file(entry["path"])
            return

        # Dossier : zoom et affichage des enfants
        children = file_system.list_dir(entry["path"])
        if not children:
            print(f"Dossier vide ou inaccessible : {entry['name']}")
            return

        self.nav_stack.append({
            "nodes":           self.current_nodes,
            "center":          LPoint3(self.current_center),
            "dist":            self.cam_dist,
            "selected_index":  self.selected_index,
            "breadcrumb_text": self.breadcrumb.getText(),
        })

        opened_pos = entry["node"].getPos(self.render)

        for other in self.current_nodes:
            if other is not entry:
                other["node"].hide()

        # Le dossier ouvert devient très transparent, son nom reste lisible
        entry["node"].setTransparency(TransparencyAttrib.MAlpha)
        entry["node"].setColorScale(1, 1, 1, PREVIOUS_LEVEL_ALPHA)
        entry["label_np"].setScale(0.55)

        depth = len(self.nav_stack)
        self._build_level(children, center=opened_pos, is_root=False,
                          depth=depth, label=entry["name"])
        self._animate_camera_to(opened_pos, new_dist=max(8, 50 - depth*10))

    def _go_back(self):
        if not self.nav_stack:
            return
        for n in self.current_nodes:
            n["node"].removeNode()

        prev = self.nav_stack.pop()
        self.current_nodes  = prev["nodes"]
        self.selected_index = prev["selected_index"]
        self.breadcrumb.setText(prev["breadcrumb_text"])

        for n in self.current_nodes:
            n["node"].show()

        # Restaure l'opacité et le label du dossier refermé
        reopened = self.current_nodes[self.selected_index]
        reopened["node"].setColorScale(1, 1, 1, 1)
        reopened["label_np"].setScale(0.35)

        self._animate_camera_to(prev["center"], new_dist=prev["dist"])

    # ---------- Construction des niveaux ----------

    def _setup_lights(self):
        # Lumiere "soleil" assez forte, placee a une vraie distance
        sun = DirectionalLight("sun")
        sun.setColor(LColor(1.0, 0.95, 0.85, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-45, -35, 0)
        self.render.setLight(sun_np)

        # Remplissage froid pour ne jamais avoir de face tout a fait noire
        fill = DirectionalLight("fill")
        fill.setColor(LColor(0.25, 0.3, 0.45, 1))
        fill_np = self.render.attachNewNode(fill)
        fill_np.setHpr(135, 25, 0)
        self.render.setLight(fill_np)

    def _fibonacci_sphere_point(self, index, total, radius):
        if total <= 1:
            return (0, 0, radius)
        golden = math.pi * (3 - math.sqrt(5))
        y_norm = 1 - (index / (total - 1)) * 2
        ring   = math.sqrt(max(0, 1 - y_norm**2))
        theta  = golden * index
        return (
            math.cos(theta) * ring * radius,
            y_norm * radius,
            math.sin(theta) * ring * radius,
        )

    def _build_level(self, entries, center, is_root,
                     depth=0, label="", offset=0):
        self.current_nodes  = []
        self.selected_index = -1
        self.breadcrumb.setText(label)

        # Mémorise pour la pagination
        self.level_full_entries = entries
        self.level_center   = LPoint3(center)
        self.level_is_root  = is_root
        self.level_depth    = depth
        self.level_label    = label
        self.level_offset   = offset

        if is_root:
            self._create_black_hole(center)

        page      = entries[offset : offset + PAGE_SIZE]
        remaining = len(entries) - (offset + len(page))

        base_radius = ORBIT_RADIUS_BY_DEPTH[min(depth, len(ORBIT_RADIUS_BY_DEPTH)-1)]
        total_slots = len(page) + (1 if remaining > 0 else 0)
        radius      = max(base_radius, total_slots * 0.9)
        depth_scale = max(0.4, 1 - depth * 0.2)

        sphere_shader = shaders.load_sphere_shader()

        for i, item in enumerate(page):
            is_folder = item["type"] == "folder"
            color = (0.4, 0.8, 1.0, 1) if is_folder else get_file_color(item["name"])
            base_scale = (1.0 if is_folder else 0.55) * depth_scale

            # Modele 3D choisi de facon stable selon le nom (toujours le meme objet)
            seed = sum(ord(c) for c in item["name"])
            if is_folder and FOLDER_MODELS:
                model_path = FOLDER_MODELS[seed % len(FOLDER_MODELS)]
            elif not is_folder and FILE_MODELS:
                model_path = FILE_MODELS[seed % len(FILE_MODELS)]
            else:
                model_path = None

            if model_path:
                node = self.loader.loadModel(model_path)
                node.reparentTo(self.render)
                node.setPos(x, y, z)
                node.setScale(base_scale)
                node.setLightOff()          # les modeles ont des textures eclairantes integrees
                node.setHpr(seed % 360, (seed // 7) % 40 - 20, 0)
                node.setColorScale(*color, 1)   # teinte le modele selon dossier/type de fichier
            else:
                node = self.loader.loadModel("models/misc/sphere")
                node.reparentTo(self.render)
                node.setPos(x, y, z)
                node.setScale(base_scale)
                node.setLightOff()
                node.setColor(*color)
                sphere_shader = shaders.load_sphere_shader()
                node.setShader(sphere_shader)
                node.setShaderInput("sphere_color", *color)
                node.setShaderInput("time", 0.0)

            # Halo de lueur autour de chaque objet
            shaders.create_glow(self.render, self.loader, node, color,
                                 scale_factor=2.0)

            # Label 3D toujours face à la caméra
            tn = TextNode(f"label_{item['name']}")
            tn.setText(item["name"])
            if is_folder:
                tn.setTextColor(0.6, 1.0, 1.0, 1)
            else:
                tn.setTextColor(1.0, 0.8, 0.5, 1)
            tn.setAlign(TextNode.ACenter)
            label_np = node.attachNewNode(tn)
            label_np.setScale(0.35)
            label_np.setPos(0, 0, 1.1)
            label_np.setBillboardPointEye()

            self.current_nodes.append({
                "node":       node,
                "name":       item["name"],
                "type":       item["type"],
                "path":       item.get("path"),
                "color":      color,
                "base_scale": base_scale,
                "label_np":   label_np,
            })

        # Indicateur de pagination
        if remaining > 0:
            ox, oy, oz = self._fibonacci_sphere_point(len(page), total_slots, radius)
            x, y, z    = center.x+ox, center.y+oy, center.z+oz
            color      = (0.6, 0.6, 0.6, 1)
            base_scale = 0.55 * depth_scale

            node = self.loader.loadModel(MORE_MODELS[0] if MORE_MODELS else "models/misc/sphere")
            node.reparentTo(self.render)
            node.setPos(x, y, z)
            node.setScale(0.6 * depth_scale)
            node.setLightOff()
            node.setColorScale(0.8, 0.8, 0.8, 1)
            node.setShader(sphere_shader)
            node.setShaderInput("sphere_color", *color)
            node.setShaderInput("time", 0.0)

            tn = TextNode("label_more")
            tn.setText(f"+{remaining} autres")
            tn.setTextColor(0.8, 0.8, 0.8, 1)
            tn.setAlign(TextNode.ACenter)
            label_np = node.attachNewNode(tn)
            label_np.setScale(0.35)
            label_np.setPos(0, 0, 1.1)
            label_np.setBillboardPointEye()

            self.current_nodes.append({
                "node":       node,
                "name":       "more",
                "type":       "more",
                "path":       None,
                "color":      color,
                "base_scale": base_scale,
                "label_np":   label_np,
            })

        if self.current_nodes:
            self.selected_index = 0
            self._set_highlight(self.current_nodes[0], True)

    def _create_black_hole(self, center):
        # Trou noir : shader animé + cœur opaque
        self.blackhole_shader_node, _ = shaders.create_accretion_disk(
            self.render, self.loader, center
        )

    # ---------- Animation continue ----------

    def _animate_task(self, task):
        self._anim_time += ClockObject.getGlobalClock().getDt()

        # Anime le disque d'accrétion du trou noir
        if hasattr(self, "blackhole_shader_node"):
            self.blackhole_shader_node.setShaderInput("time", self._anim_time)

        # Scintillement des étoiles de fond
        for star in getattr(self, "starfield", []):
            star.setShaderInput("time", self._anim_time)

        dt = ClockObject.getGlobalClock().getDt()
        for entry in self.current_nodes:
            entry["node"].setShaderInput("time", self._anim_time)
            if entry["type"] == "folder":
                entry["node"].setH(entry["node"].getH() + dt * 5)
            elif entry["type"] == "file":
                entry["node"].setHpr(entry["node"].getH() + dt * 8,
                                     entry["node"].getP() + dt * 3, 0)

        return task.cont


    def _create_black_hole(self, center):
        self.blackhole_shader_node, _ = shaders.create_accretion_disk(
            self.render, self.loader, center
        )
        # Station orbitale autour du trou noir
        station = self.loader.loadModel("assets/models/Base Large.glb")
        station.reparentTo(self.render)
        station.setPos(center + LPoint3(0, 12, 4))
        station.setScale(1.5)
        station.setLightOff()
        station.setHpr(20, 0, 0)

app = GestureDesktopApp()
app.run()

