#version 330

in vec3 vNormal;
in vec3 vPosition;
in vec2 vTexCoord;

uniform vec4 sphere_color;
uniform float time;

out vec4 fragColor;

void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(-vPosition);

    // Lumière principale depuis le centre de la scène
    vec3 lightDir = normalize(-vPosition + vec3(0.0, 0.0, 5.0));

    // Diffuse
    float diff = max(dot(normal, lightDir), 0.0);

    // Specular (Blinn-Phong)
    vec3 halfVec = normalize(lightDir + viewDir);
    float spec = pow(max(dot(normal, halfVec), 0.0), 64.0);

    // Fresnel : bord lumineux pour l'effet spatial
    float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.0);

    // Couleur finale
    vec3 ambient = sphere_color.rgb * 0.15;
    vec3 diffuse = sphere_color.rgb * diff * 0.7;
    vec3 specular = vec3(1.0, 1.0, 1.0) * spec * 0.5;
    vec3 rim = sphere_color.rgb * fresnel * 1.2;

    vec3 color = ambient + diffuse + specular + rim;
    fragColor = vec4(color, sphere_color.a);
}