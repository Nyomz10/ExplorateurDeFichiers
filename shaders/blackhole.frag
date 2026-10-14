#version 330

in vec3 vNormal;
in vec3 vPosition;
in vec2 vTexCoord;

uniform float time;

out vec4 fragColor;

void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(-vPosition);

    // Fresnel fort pour l'effet de distorsion gravitationnelle sur les bords
    float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 4.0);

    // Disque d'accrétion simulé sur l'équateur
    float equator = abs(dot(normal, vec3(0.0, 0.0, 1.0)));
    float disk = smoothstep(0.85, 1.0, 1.0 - equator);

    // Animation du disque
    float angle = atan(vTexCoord.y - 0.5, vTexCoord.x - 0.5);
    float spin = sin(angle * 6.0 + time * 0.8) * 0.5 + 0.5;

    vec3 diskColor = mix(
        vec3(0.0, 0.4, 1.0),  // bleu intérieur
        vec3(0.8, 0.5, 0.0),  // orange chaud extérieur
        spin
    );

    vec3 rimColor = vec3(0.1, 0.5, 1.0) * fresnel * 2.0;
    vec3 finalColor = rimColor + diskColor * disk * (1.0 - fresnel * 0.5);

    float alpha = max(fresnel * 0.9, disk * 0.8);
    if (alpha < 0.02) discard;

    fragColor = vec4(finalColor, alpha);
}