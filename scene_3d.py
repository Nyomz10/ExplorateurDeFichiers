from direct.showbase.ShowBase import ShowBase
from panda3d.core import PointLight, AmbientLight, LColor, TextNode, LPoint3, ClockObject, TransparencyAttrib
from direct.gui.OnscreenText import OnscreenText
import math
import cv2
import mediapipe as mp
import file_system
import gestures
import shaders


ORBIT_RADIUS_BY_DEPTH = [13, 6, 3]
MAX_ITEMS_PER_LEVEL = 15
DOUBLE_FIST_WINDOW = 0.7  # délai max entre les deux poings pour compter comme "double poing"
ROTATE_SENSITIVITY = 300  # plus haut = rotation plus rapide pour un même déplacement de main
ZOOM_SENSITIVITY = 50
MIN_CAM_DIST = 6
MAX_CAM_DIST = 60
GESTURE_COOLDOWN = 2  # secondes minimum entre deux sélections/ouvertures pour éviter les répétitions
PREVIOUS_LEVEL_ALPHA = 0.15  # opacité des dossiers parents traversés
PAGE_SIZE = MAX_ITEMS_PER_LEVEL - 1  # une place réservée à l'indicateur "+X autres" si besoin
FLIP_THRESHOLD = 0.01  # valeur absolue minimum du produit vectoriel pour considérer la main "clairement retournée"

FILE_TYPE_COLORS = {
    # Images : violet/magenta
    ".png": (0.8, 0.3, 0.9, 1), ".jpg": (0.8, 0.3, 0.9, 1), ".jpeg": (0.8, 0.3, 0.9, 1),
    ".gif": (0.8, 0.3, 0.9, 1), ".bmp": (0.8, 0.3, 0.9, 1), ".svg": (0.8, 0.3, 0.9, 1),
    ".webp": (0.8, 0.3, 0.9, 1),
    # Vidéos : rouge
    ".mp4": (0.9, 0.25, 0.25, 1), ".mkv": (0.9, 0.25, 0.25, 1), ".avi": (0.9, 0.25, 0.25, 1),
    ".mov": (0.9, 0.25, 0.25, 1), ".webm": (0.9, 0.25, 0.25, 1),
    # Audio : vert
    ".mp3": (0.3, 0.9, 0.4, 1), ".wav": (0.3, 0.9, 0.4, 1), ".flac": (0.3, 0.9, 0.4, 1),
    ".ogg": (0.3, 0.9, 0.4, 1), ".m4a": (0.3, 0.9, 0.4, 1),
    # Documents texte/PDF : jaune
    ".pdf": (1.0, 0.85, 0.3, 1), ".doc": (1.0, 0.85, 0.3, 1), ".docx": (1.0, 0.85, 0.3, 1),
    ".txt": (1.0, 0.85, 0.3, 1), ".md": (1.0, 0.85, 0.3, 1), ".rtf": (1.0, 0.85, 0.3, 1),
    # Tableurs/présentations : orange clair
    ".xls": (1.0, 0.6, 0.2, 1), ".xlsx": (1.0, 0.6, 0.2, 1), ".csv": (1.0, 0.6, 0.2, 1),
    ".ppt": (1.0, 0.6, 0.2, 1), ".pptx": (1.0, 0.6, 0.2, 1),
    # Code/scripts : cyan clair
    ".py": (0.3, 0.9, 0.9, 1), ".js": (0.3, 0.9, 0.9, 1), ".html": (0.3, 0.9, 0.9, 1),
    ".css": (0.3, 0.9, 0.9, 1), ".json": (0.3, 0.9, 0.9, 1), ".cpp": (0.3, 0.9, 0.9, 1),
    ".java": (0.3, 0.9, 0.9, 1),
    # Archives : gris-bleu
    ".zip": (0.5, 0.5, 0.7, 1), ".rar": (0.5, 0.5, 0.7, 1), ".7z": (0.5, 0.5, 0.7, 1),
}

DEFAULT_FILE_COLOR = (0.8, 0.8, 0.8, 1)  # type inconnu : gris clair


def get_file_color(name):
    # Récupère la couleur associée à l'extension du fichier
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return FILE_TYPE_COLORS.get(ext, DEFAULT_FILE_COLOR)


class GestureDesktopApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        # Maintient le ratio d'aspect correct quand la fenêtre est redimensionnée
        self.accept("window-event", self._on_window_resize)
        self.setBackgroundColor(0.004, 0.006, 0.018, 1)
        self.disableMouse()

        self.cam_h = 0
        self.cam_p = 0
        self.cam_dist = 40
        self.current_center = LPoint3(0, 0, 0)

        self.nav_stack = []
        self.selected_index = -1
        self.current_nodes = []
        self.orbital_ring = None
        # Mémorise les infos du niveau affiché pour pouvoir paginer sans changer de niveau
        self.level_full_entries = []
        self.level_center = LPoint3(0, 0, 0)
        self.level_is_root = True
        self.level_depth = 0
        self.level_label = ""
        self.level_offset = 0

        self._setup_lights()

        self.breadcrumb = OnscreenText(
            text="Ce PC", pos=(0, 0.9), scale=0.07,
            fg=(0.8, 1.0, 1.0, 1), align=TextNode.ACenter
        )
        self.gesture_label = OnscreenText(
            text="", pos=(0, 0.8), scale=0.05,
            fg=(1.0, 1.0, 0.4, 1), align=TextNode.ACenter
        )

        root_path = file_system.get_root_path()
        root_entries = file_system.list_dir(root_path)
        self._build_level(root_entries, center=LPoint3(0, 0, 0), is_root=True, depth=0, label="Ce PC")
        self._update_camera()

        # Champ d'étoiles de fond
        self.starfield = shaders.create_starfield(self.render, self.loader)
        # Anneau orbital pour l'élément sélectionné (créé dynamiquement)
        self.orbital_ring = None

        # Contrôles clavier (toujours actifs en secours)
        self.accept("arrow_left-repeat", self._rotate, ["h", -3])
        self.accept("arrow_right-repeat", self._rotate, ["h", 3])
        self.accept("arrow_up-repeat", self._rotate, ["p", 3])
        self.accept("arrow_down-repeat", self._rotate, ["p", -3])
        self.accept("arrow_left", self._rotate, ["h", -3])
        self.accept("arrow_right", self._rotate, ["h", 3])
        self.accept("arrow_up", self._rotate, ["p", 3])
        self.accept("arrow_down", self._rotate, ["p", -3])
        self.accept("tab", self._next_star)
        self.accept("enter", self._open_selected)
        self.accept("backspace", self._go_back)
        self.accept("escape", self.userExit)
        self.accept("escape", quit)

        OnscreenText(
            text="pincement+déplacer = tourner | 2 mains pincées = zoom | index+majeur = sélectionner | double poing = ouvrir | retourner la main ouverte = retour",
            pos=(0, -0.9), scale=0.04,
            fg=(0.3, 0.7, 1.0, 1), align=TextNode.ACenter
        )
        
        OnscreenText(
            text="Clavier : flèches orbiter | Tab sélectionner | Entrée ouvrir | Retour arrière | Échap quitter",
            pos=(0, -0.97), scale=0.04,
            fg=(0.3, 0.7, 1.0, 1), align=TextNode.ACenter
        )

        self._setup_hand_tracking()
        # Tâche d'animation continue (pulse des sphères, rotation du disque)
        self.taskMgr.add(self._animate_task, "animate")
        self._anim_time = 0.0
        self.taskMgr.add(self._gesture_update_task, "gesture_update")

    # ---------- Suivi des mains ----------

    def _setup_hand_tracking(self):
        self.cap = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.6
        )
        # États utilisés pour détecter les déplacements et éviter les déclenchements répétés
        self.prev_single_pinch_pos = None
        self.prev_two_hand_dist = None
        self.was_pointing = False
        self.was_fist = False
        self.last_action_time = 0.0
        self.last_fist_press_time = None
        self.fist_orientation_start = None


    def _on_window_event(self, window):
        # Gère le redimensionnement de la fenêtre et la perte de focus
        wp = window.getProperties()
        if wp.getXSize() > 0 and wp.getYSize() > 0:
            ratio = wp.getXSize() / wp.getYSize()
            self.camLens.setAspectRatio(ratio)

    def _gesture_update_task(self, task):
        ok, frame = self.cap.read()
        if not ok:
            return task.cont

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        now = ClockObject.getGlobalClock().getFrameTime()
        label_text = ""

        hands_data = []
        if result.multi_hand_landmarks and result.multi_handedness:
            for lm, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
                hands_data.append({
                    "landmarks": lm,
                    "label": gestures.get_hand_label(handedness),
                    "pinching": gestures.is_pinching(lm),
                    "pointing": gestures.is_index_pointing(lm),
                })

        right_hand = next((h for h in hands_data if h["label"] == "Right"), None)
        left_hand = next((h for h in hands_data if h["label"] == "Left"), None)
        pinching_hands = [h for h in hands_data if h["pinching"]]

        # --- Zoom à deux mains pincées ---
        if len(pinching_hands) == 2:
            a = gestures.get_wrist_pos(pinching_hands[0]["landmarks"])
            b = gestures.get_wrist_pos(pinching_hands[1]["landmarks"])
            dist = math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
            if self.prev_two_hand_dist is not None:
                delta = dist - self.prev_two_hand_dist
                self.cam_dist -= delta * ZOOM_SENSITIVITY
                # Limite minimale adaptée à la profondeur courante
                depth = len(self.nav_stack)
                adapted_min = max(1.5, MIN_CAM_DIST - depth * 1.5)
                self.cam_dist = max(adapted_min, min(MAX_CAM_DIST, self.cam_dist))
                self._update_camera()
            self.prev_two_hand_dist = dist
            self.prev_single_pinch_pos = None
            label_text = "ZOOM"

        # --- Rotation avec une seule main pincée ---
        elif len(pinching_hands) == 1:
            pos = gestures.get_wrist_pos(pinching_hands[0]["landmarks"])
            if self.prev_single_pinch_pos is not None:
                dx = pos[0] - self.prev_single_pinch_pos[0]
                dy = pos[1] - self.prev_single_pinch_pos[1]
                self.cam_h -= dx * ROTATE_SENSITIVITY
                self.cam_p = max(-89, min(89, self.cam_p + dy * ROTATE_SENSITIVITY))
                self._update_camera()
            self.prev_single_pinch_pos = pos
            self.prev_two_hand_dist = None
            label_text = "ROTATION"

        else:
            self.prev_single_pinch_pos = None
            self.prev_two_hand_dist = None


        # --- Sélection avec index + majeur levés (toutes mains confondues) ---
        pointing_now = any(gestures.is_two_fingers(h["landmarks"]) for h in hands_data)
        if pointing_now and not self.was_pointing and (now - self.last_action_time) > GESTURE_COOLDOWN:
            self._select_nearest_to_camera()
            self.last_action_time = now
            label_text = "SÉLECTION"
        self.was_pointing = pointing_now

        # --- Ouverture avec double poing fermé rapproché (comme un double-clic) ---
        fist_now = any(h["landmarks"] and gestures.is_fist(h["landmarks"]) and not h["pinching"] for h in hands_data)
        if fist_now and not self.was_fist:
            if self.last_fist_press_time is not None and (now - self.last_fist_press_time) < DOUBLE_FIST_WINDOW:
                self._open_selected()
                self.last_action_time = now
                self.last_fist_press_time = None
                label_text = "OUVERTURE"
            else:
                self.last_fist_press_time = now
        self.was_fist = fist_now


        # --- Retour arrière avec la main DROITE ouverte qu'on retourne uniquement ---
        right_open = (
            right_hand
            if right_hand is not None
            and gestures.is_open_palm(right_hand["landmarks"])
            and not right_hand["pinching"]
            and len(pinching_hands) == 0
            else None
        )
        open_hand = right_open

        if open_hand is not None:
            orientation = gestures.get_hand_orientation(open_hand["landmarks"])
            if self.fist_orientation_start is None:
                # Ne commence à tracker que si la main est clairement dans un sens
                if abs(orientation) > FLIP_THRESHOLD:
                    self.fist_orientation_start = orientation
            else:
                flipped = (orientation > 0) != (self.fist_orientation_start > 0)
                # Déclenche seulement si le nouvel angle est lui aussi clairement défini
                if flipped and abs(orientation) > FLIP_THRESHOLD and (now - self.last_action_time) > GESTURE_COOLDOWN:
                    self._go_back()
                    self.last_action_time = now
                    self.fist_orientation_start = None
                    label_text = "RETOUR"
        else:
            self.fist_orientation_start = None


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
        x = self.cam_dist * math.cos(rad_p) * math.sin(rad_h)
        y = -self.cam_dist * math.cos(rad_p) * math.cos(rad_h)
        z = self.cam_dist * math.sin(rad_p)
        self.camera.setPos(self.current_center + LPoint3(x, y, z))
        self.camera.lookAt(self.current_center)

    def _animate_camera_to(self, new_center, new_dist, duration=1.0):
        start_center = LPoint3(self.current_center)
        start_dist = self.cam_dist
        self._transition = {
            "t": 0.0,
            "duration": duration,
            "start_center": start_center,
            "end_center": LPoint3(new_center),
            "start_dist": start_dist,
            "end_dist": new_dist,
        }
        self.taskMgr.add(self._transition_task, "cam_transition")

    def _transition_task(self, task):
        tr = self._transition
        tr["t"] += ClockObject.getGlobalClock().getDt()
        ratio = min(tr["t"] / tr["duration"], 1.0)
        ease = 1 - (1 - ratio) ** 2
        self.current_center = tr["start_center"] + (tr["end_center"] - tr["start_center"]) * ease
        self.cam_dist = tr["start_dist"] + (tr["end_dist"] - tr["start_dist"]) * ease
        self._update_camera()
        if ratio >= 1.0:
            return task.done
        return task.cont

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
        nearest_index = min(
            range(len(self.current_nodes)),
            key=lambda i: (self.current_nodes[i]["node"].getPos(self.render) - cam_pos).length()
        )
        if self.selected_index >= 0:
            self._set_highlight(self.current_nodes[self.selected_index], False)
        self.selected_index = nearest_index
        self._set_highlight(self.current_nodes[self.selected_index], True)

    def _set_highlight(self, entry, active):
        node = entry["node"]
        if active:
            node.setColor(0.0, 1.0, 1.0, 1)
            node.setScale(entry["base_scale"] * 1.4)
            # Ajoute un anneau orbital autour de l'élément sélectionné
            if self.orbital_ring is not None:
                self.orbital_ring.removeNode()
            self.orbital_ring = shaders.create_orbital_ring(
                self.render, node, (0.0, 1.0, 1.0, 1), radius=entry["base_scale"] * 2.2
            )
        else:
            node.setColor(*entry["color"])
            node.setScale(entry["base_scale"])
            # Retire l'anneau orbital
            if self.orbital_ring is not None:
                self.orbital_ring.removeNode()
                self.orbital_ring = None

    # ---------- Ouverture / retour ----------

    def _open_selected(self):
        if self.selected_index < 0 or not self.current_nodes:
            return
        entry = self.current_nodes[self.selected_index]

        if entry["type"] == "more":
            # Détruit les nœuds de la page actuelle avant de charger la suivante
            for node_entry in self.current_nodes:
                node_entry["node"].removeNode()

            next_offset = self.level_offset + PAGE_SIZE
            self._build_level(
                self.level_full_entries, center=self.level_center,
                is_root=self.level_is_root, depth=self.level_depth,
                label=self.level_label, offset=next_offset
            )
            return

        if entry["type"] == "file":
            file_system.open_file(entry["path"])
            return

        children = file_system.list_dir(entry["path"])
        if not children:
            print(f"Le dossier {entry['name']} est vide ou inaccessible")
            return

        self.nav_stack.append({
            "nodes": self.current_nodes,
            "center": LPoint3(self.current_center),
            "dist": self.cam_dist,
            "selected_index": self.selected_index,
            "breadcrumb_text": self.breadcrumb.getText(),
        })

        opened_world_pos = entry["node"].getPos(self.render)

        for other in self.current_nodes:
            if other is not entry:
                other["node"].hide()

        # Le dossier qu'on vient d'ouvrir devient quasi transparent, mais son nom reste lisible au centre
        entry["node"].setTransparency(TransparencyAttrib.MAlpha)
        entry["node"].setColorScale(1, 1, 1, PREVIOUS_LEVEL_ALPHA)
        entry["label_np"].setScale(0.55)

        depth = len(self.nav_stack)
        self._build_level(children, center=opened_world_pos, is_root=False, depth=depth, label=entry["name"])

        # Distance adaptée à la profondeur : plus on descend, plus on zoome près
        adapted_dist = max(8, 50 - depth * 10)
        self._animate_camera_to(opened_world_pos, new_dist=adapted_dist)

    def _go_back(self):
        if not self.nav_stack:
            return

        for entry in self.current_nodes:
            entry["node"].removeNode()

        previous = self.nav_stack.pop()
        self.current_nodes = previous["nodes"]
        self.selected_index = previous["selected_index"]
        self.breadcrumb.setText(previous["breadcrumb_text"])

        for entry in self.current_nodes:
            entry["node"].show()

        # Restaure l'opacité complète du dossier qu'on vient de refermer
        reopened_entry = self.current_nodes[self.selected_index]
        reopened_entry["node"].setColorScale(1, 1, 1, 1)
        reopened_entry["label_np"].show()

        self._animate_camera_to(previous["center"], new_dist=previous["dist"])

    # ---------- Construction des niveaux ----------

    def _setup_lights(self):
        ambient = AmbientLight("ambient")
        ambient.setColor(LColor(0.15, 0.15, 0.3, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        plight = PointLight("center_light")
        plight.setColor(LColor(0.3, 0.7, 1.0, 1))
        plnp = self.render.attachNewNode(plight)
        plnp.setPos(0, 0, 0)
        self.render.setLight(plnp)

    def _fibonacci_sphere_point(self, index, total, radius):
        if total <= 1:
            return (0, 0, radius)
        golden_angle = math.pi * (3 - math.sqrt(5))
        y_norm = 1 - (index / (total - 1)) * 2
        ring_radius = math.sqrt(max(0, 1 - y_norm * y_norm))
        theta = golden_angle * index
        x = math.cos(theta) * ring_radius * radius
        z = math.sin(theta) * ring_radius * radius
        y = y_norm * radius
        return (x, y, z)

    def _build_level(self, entries, center, is_root, depth=0, label="", offset=0, reset_camera_center=True):
        self.current_nodes = []
        self.selected_index = -1
        self.breadcrumb.setText(label)

        # Mémorise le niveau pour permettre la pagination
        self.level_full_entries = entries
        self.level_center = LPoint3(center)
        self.level_is_root = is_root
        self.level_depth = depth
        self.level_label = label
        self.level_offset = offset

        if is_root:
            self._create_black_hole(center)

        page = entries[offset:offset + PAGE_SIZE]
        remaining = len(entries) - (offset + len(page))

        base_radius = ORBIT_RADIUS_BY_DEPTH[min(depth, len(ORBIT_RADIUS_BY_DEPTH) - 1)]
        total_slots = len(page) + (1 if remaining > 0 else 0)
        radius = max(base_radius, total_slots * 0.9)
        depth_scale = max(0.4, 1 - depth * 0.2)

        for i, item in enumerate(page):
            x, y, z = self._fibonacci_sphere_point(i, total_slots, radius)
            x += center.x
            y += center.y
            z += center.z

            is_folder = item["type"] == "folder"
            color = (0.4, 0.8, 1.0, 1) if is_folder else get_file_color(item["name"])
            base_scale = (0.7 if is_folder else 0.45) * depth_scale

            node = self.loader.loadModel("models/misc/sphere")
            node.reparentTo(self.render)
            node.setPos(x, y, z)
            node.setScale(base_scale)
            node.setColor(*color)
            node.setLightOff()
            # Shader sphère : Fresnel + Phong pour un rendu volumétrique
            sphere_shader = shaders.load_sphere_shader()
            node.setShader(sphere_shader)
            node.setShaderInput("sphere_color", *color)
            node.setShaderInput("time", 0.0)
            # Halo de lueur autour de chaque étoile/planète
            shaders.create_glow(self.render, self.loader, node, color, scale_factor=2.0)

            tn = TextNode(f"label_{item['name']}")
            tn.setText(item["name"])
            tn.setTextColor(0.6, 1.0, 1.0, 1) if is_folder else tn.setTextColor(1.0, 0.8, 0.5, 1)
            tn.setAlign(TextNode.ACenter)
            label_np = node.attachNewNode(tn)
            label_np.setScale(0.35)
            label_np.setPos(0, 0, 1.1)
            label_np.setBillboardPointEye()

            self.current_nodes.append({
                "node": node, "name": item["name"], "type": item["type"],
                "path": item.get("path"), "color": color, "base_scale": base_scale,
                "label_np": label_np,
            })

        # Indicateur de pagination : sphère grise avec le nombre d'éléments restants
        if remaining > 0:
            x, y, z = self._fibonacci_sphere_point(len(page), total_slots, radius)
            x += center.x
            y += center.y
            z += center.z

            color = (0.6, 0.6, 0.6, 1)
            base_scale = 0.55 * depth_scale

            node = self.loader.loadModel("models/misc/sphere")
            node.reparentTo(self.render)
            node.setPos(x, y, z)
            node.setScale(base_scale)
            node.setColor(*color)
            node.setLightOff()

            tn = TextNode("label_more")
            tn.setText(f"+{remaining} autres")
            tn.setTextColor(0.8, 0.8, 0.8, 1)
            tn.setAlign(TextNode.ACenter)
            label_np = node.attachNewNode(tn)
            label_np.setScale(0.35)
            label_np.setPos(0, 0, 1.1)
            label_np.setBillboardPointEye()

            self.current_nodes.append({
                "node": node, "name": "more", "type": "more",
                "path": None, "color": color, "base_scale": base_scale,
                "label_np": label_np,
            })

        if self.current_nodes:
            self.selected_index = 0
            self._set_highlight(self.current_nodes[0], True)

    def _create_black_hole(self, center):
        # Trou noir avec shader GLSL et disque d'accrétion animé
        self.blackhole_shader_node, _ = shaders.create_accretion_disk(
            self.render, self.loader, center
        )

    def _on_window_resize(self, window):
        # Recalcule le ratio d'aspect de la caméra quand la fenêtre change de taille
        wp = window.getProperties()
        if wp.getXSize() > 0 and wp.getYSize() > 0:
            ratio = wp.getXSize() / wp.getYSize()
            self.camLens.setAspectRatio(ratio)

    def _animate_task(self, task):
        self._anim_time += ClockObject.getGlobalClock().getDt()

        # Temps du disque d'accretion
        if hasattr(self, "blackhole_shader_node"):
            self.blackhole_shader_node.setShaderInput("time", self._anim_time)

        # Scintillement des etoiles de fond
        for star in getattr(self, "starfield", []):
            star.setShaderInput("time", self._anim_time)

        # Pulse leger + temps pour chaque planete
        for i, entry in enumerate(self.current_nodes):
            entry["node"].setShaderInput("time", self._anim_time)
            if i == self.selected_index:
                continue
            base = entry["base_scale"]
            pulse = 1.0 + 0.04 * math.sin(self._anim_time * 1.5 + i)
            entry["node"].setScale(base * pulse)

        return task.cont


app = GestureDesktopApp()
app.run()