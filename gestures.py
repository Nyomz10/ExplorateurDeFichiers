import math

PINCH_THRESHOLD = 0.05


def distance(a, b):
    # Distance euclidienne 3D entre deux landmarks MediaPipe
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def is_pinching(hand_landmarks):
    # Pouce (4) et index (8) suffisamment proches
    return distance(hand_landmarks.landmark[4], hand_landmarks.landmark[8]) < PINCH_THRESHOLD


def is_index_pointing(hand_landmarks):
    # Index tendu (bout au-dessus de l'articulation) et les 3 autres doigts repliés
    lm = hand_landmarks.landmark
    index_extended = lm[8].y < lm[6].y
    middle_folded = lm[12].y > lm[10].y
    ring_folded = lm[16].y > lm[14].y
    pinky_folded = lm[20].y > lm[18].y
    return index_extended and middle_folded and ring_folded and pinky_folded


def get_wrist_pos(hand_landmarks):
    w = hand_landmarks.landmark[0]
    return (w.x, w.y)


def get_hand_label(handedness):
    # "Left" ou "Right" détecté par MediaPipe
    return handedness.classification[0].label


def is_index_pointing(hand_landmarks):
    # Index tendu, les 3 autres doigts repliés (le pouce n'est pas vérifié, trop variable)
    lm = hand_landmarks.landmark
    index_up = lm[8].y < lm[6].y
    middle_down = lm[12].y > lm[10].y
    ring_down = lm[16].y > lm[14].y
    pinky_down = lm[20].y > lm[18].y
    return index_up and middle_down and ring_down and pinky_down


def is_fist(hand_landmarks):
    # Les 4 doigts (hors pouce) sont repliés : bout en dessous de l'articulation médiane
    lm = hand_landmarks.landmark
    index_down = lm[8].y > lm[6].y
    middle_down = lm[12].y > lm[10].y
    ring_down = lm[16].y > lm[14].y
    pinky_down = lm[20].y > lm[18].y
    return index_down and middle_down and ring_down and pinky_down

def is_open_palm(hand_landmarks):
    # Les 4 doigts (hors pouce) sont tendus : bout au-dessus de l'articulation médiane
    lm = hand_landmarks.landmark
    index_up = lm[8].y < lm[6].y
    middle_up = lm[12].y < lm[10].y
    ring_up = lm[16].y < lm[14].y
    pinky_up = lm[20].y < lm[18].y
    return index_up and middle_up and ring_up and pinky_up

def is_two_fingers(hand_landmarks):
    # Index et majeur tendus, annulaire et auriculaire repliés
    lm = hand_landmarks.landmark
    index_up = lm[8].y < lm[6].y
    middle_up = lm[12].y < lm[10].y
    ring_down = lm[16].y > lm[14].y
    pinky_down = lm[20].y > lm[18].y
    return index_up and middle_up and ring_down and pinky_down


def get_hand_orientation(hand_landmarks):
    # Produit vectoriel entre deux axes de la paume pour détecter le sens d'orientation
    lm = hand_landmarks.landmark
    wrist = lm[0]
    index_mcp = lm[5]
    pinky_mcp = lm[17]
    v1x, v1y = index_mcp.x - wrist.x, index_mcp.y - wrist.y
    v2x, v2y = pinky_mcp.x - wrist.x, pinky_mcp.y - wrist.y
    cross = v1x * v2y - v1y * v2x
    return cross
