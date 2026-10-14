#version 330

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_NormalMatrix;

in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;

out vec3 vNormal;
out vec3 vPosition;
out vec2 vTexCoord;

void main() {
    vec4 pos = p3d_ModelViewMatrix * p3d_Vertex;
    vPosition = pos.xyz;
    vNormal = normalize(mat3(p3d_NormalMatrix) * p3d_Normal);
    vTexCoord = p3d_MultiTexCoord0;
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}