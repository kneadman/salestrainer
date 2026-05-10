import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const vertexShader = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position, 1.0);
}
`;

const fragmentShader = `
precision mediump float;
varying vec2 vUv;
uniform vec3 uColor1;
uniform vec3 uColor2;
uniform float uOpacity;
uniform vec2 uCenter;

void main() {
  vec2 center = vec2(0.5) + uCenter;
  float dist = distance(vUv, center);
  float radial = smoothstep(0.0, 0.7, 1.0 - dist);
  float angle = atan(vUv.y - center.y, vUv.x - center.x) / (3.14159 * 2.0);
  vec3 gradientColor = mix(uColor1, uColor2, angle + 0.5);
  float glowStrength = radial * 0.35 * uOpacity;
  gl_FragColor = vec4(gradientColor, glowStrength);
}
`;

function hexToVec3(hex: string): THREE.Vector3 {
  const c = new THREE.Color(hex);
  return new THREE.Vector3(c.r, c.g, c.b);
}

const AmbientGlow: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Check mobile
    const isMobile = window.innerWidth < 768;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: false,
      powerPreference: isMobile ? 'low-power' : 'high-performance',
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2));
    rendererRef.current = renderer;

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const layers: { mesh: THREE.Mesh; uniforms: Record<string, THREE.IUniform> }[] = [];

    const createLayer = (
      color1: string,
      color2: string,
      opacity: number,
      centerX: number,
      centerY: number
    ) => {
      const geometry = new THREE.PlaneGeometry(2, 2);
      const uniforms = {
        uColor1: { value: hexToVec3(color1) },
        uColor2: { value: hexToVec3(color2) },
        uOpacity: { value: opacity },
        uCenter: { value: new THREE.Vector2(centerX, centerY) },
      };
      const material = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.renderOrder = -1;
      scene.add(mesh);
      layers.push({ mesh, uniforms });
    };

    if (isMobile) {
      createLayer('#0f1729', '#5eead4', 0.12, 0, 0);
    } else {
      createLayer('#0f1729', '#5eead4', 0.15, 0, 0);
      createLayer('#0f1729', '#38bdf8', 0.08, 0.2, -0.1);
      createLayer('#0f1729', '#2dd4bf', 0.06, -0.2, 0.1);
    }

    // Animation loop
    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    // GSAP scroll-driven animation
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: 'body',
        start: 'top top',
        end: 'bottom bottom',
        scrub: true,
      },
    });

    if (!isMobile && layers.length >= 3) {
      tl.to(layers[0].mesh.position, { x: 0.2, y: -0.1, ease: 'none' }, 0)
        .to(layers[0].uniforms.uCenter.value, { x: 0.1, y: 0.1, duration: 1, ease: 'none' }, 0)
        .to(layers[1].uniforms.uOpacity, { value: 0.15, duration: 1, ease: 'none' }, 0.5)
        .to(layers[2].uniforms.uCenter.value, { x: -0.2, y: 0.1, duration: 1, ease: 'none' }, 1);
    }

    // Resize handler
    const handleResize = () => {
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      tl.kill();
      layers.forEach((l) => {
        l.mesh.geometry.dispose();
        (l.mesh.material as THREE.ShaderMaterial).dispose();
      });
      renderer.dispose();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 z-0 pointer-events-none"
      style={{ width: '100%', height: '100%' }}
    />
  );
};

export default React.memo(AmbientGlow);
