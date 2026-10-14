#version 330

in vec2 vTexCoord;

uniform vec4 glow_color;

out vec4 fragColor;

void main() {
    // Halo gaussien : coeur brillant + falloff doux
    vec2 d = vTexCoord - vec2(0.5);
    float r = length(d) * 2.0;  // 0 au centre, 1 au bord
    float falloff = exp(-r * r * 4.0);
    float core = exp(-r * r * 18.0);

    float alpha = clamp((falloff * 0.7 + core) * glow_color.a, 0.0, 1.0);
    vec3 color = glow_color.rgb * (falloff * 0.8 + core * 1.4);
    fragColor = vec4(color, alpha);
}