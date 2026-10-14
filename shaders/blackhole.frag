#version 330

in vec3 vNormal;
in vec3 vPosition;
in vec2 vTexCoord;

uniform float time;

out vec4 fragColor;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
               mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(-vPosition);

    vec2 d = vTexCoord - 0.5;
    float r = length(d) * 2.0;
    float angle = atan(d.y, d.x);

    // Anneau de photons : lisere tres fin et chaud (lentille gravitationnelle)
    float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 6.0);
    float photonRing = smoothstep(0.90, 0.99, fresnel);

    // Disque d'accretion turbulent
    float spin = angle + time * 0.9 - r * 4.0;
    float turb = noise(vec2(spin * 3.0, r * 14.0)) * 0.6
               + noise(vec2(spin * 8.0, r * 30.0)) * 0.4;
    float band = smoothstep(0.15, 0.55, r) * (1.0 - smoothstep(0.75, 1.05, r));
    float disk = band * (0.35 + 0.65 * turb);

    // Effet Doppler : le cote qui s'approche est plus brillant
    float doppler = 1.0 + 0.8 * sin(angle);
    vec3 diskHot = vec3(1.0, 0.82, 0.5);
    vec3 diskCool = vec3(0.65, 0.35, 0.12);
    vec3 diskColor = mix(diskCool, diskHot, turb) * doppler;

    vec3 rimColor = vec3(1.0, 0.75, 0.4) * photonRing * 1.6;
    vec3 glowEdge = vec3(0.25, 0.45, 0.9) * pow(fresnel, 0.5) * 0.35;

    vec3 color = rimColor + glowEdge + diskColor * disk * 1.3;
    float alpha = clamp(photonRing * 1.2 + disk * 0.85 + fresnel * 0.25, 0.0, 1.0);
    if (alpha < 0.02) discard;

    fragColor = vec4(color, alpha);
}