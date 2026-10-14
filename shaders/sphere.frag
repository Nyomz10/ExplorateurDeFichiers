#version 330

in vec3 vNormal;
in vec3 vPosition;
in vec2 vTexCoord;

uniform vec4 sphere_color;
uniform float time;

out vec4 fragColor;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(-vPosition);

    // Lumiere douce venant du cote camera : objets toujours lisibles
    vec3 lightDir = normalize(vec3(-0.35, 0.5, 1.0));
    float diff = max(dot(normal, lightDir), 0.0);
    float softDiff = pow(diff, 0.8);

    // Speculaire doux
    vec3 halfVec = normalize(lightDir + viewDir);
    float spec = pow(max(dot(normal, halfVec), 0.0), 90.0);

    // Fresnel : lisere atmospherique bleute sur les bords
    float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 2.5);

    // Scintillement spatial tres leger
    float twinkle = 0.95 + 0.05 * sin(time * 2.0 + hash(vTexCoord * 40.0) * 6.2831);

    vec3 ambient = sphere_color.rgb * 0.22;
    vec3 diffuse = sphere_color.rgb * softDiff * 0.85;
    vec3 specular = vec3(0.9, 0.95, 1.0) * spec * 0.6;
    vec3 rim = vec3(0.45, 0.65, 1.0) * fresnel * 0.9;

    vec3 color = (ambient + diffuse + rim) * twinkle + specular;
    fragColor = vec4(color, sphere_color.a);
}