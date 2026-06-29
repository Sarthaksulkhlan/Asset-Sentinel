import React, { useEffect, useRef } from "react";

const ShaderBackground = React.memo(function ShaderBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext("webgl", {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: "low-power",
      preserveDrawingBuffer: false
    });
    if (!gl) {
      console.error("WebGL not supported");
      return;
    }

    const vsSource = `
      attribute vec2 a_position;
      varying vec2 v_texCoord;
      void main() {
        v_texCoord = a_position * 0.5 + 0.5;
        gl_Position = vec4(a_position, 0.0, 1.0);
      }
    `;

    const fsSource = `
      precision highp float;
      uniform float u_time;
      uniform vec2 u_resolution;
      varying vec2 v_texCoord;

      float hash(vec2 p) {
          p = fract(p * vec2(123.34, 456.21));
          p += dot(p, p + 45.32);
          return fract(p.x * p.y);
      }

      float noise(vec2 p) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          float a = hash(i);
          float b = hash(i + vec2(1.0, 0.0));
          float c = hash(i + vec2(0.0, 1.0));
          float d = hash(i + vec2(1.0, 1.0));
          vec2 u = f * f * (3.0 - 2.0 * f);
          return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
      }

      void main() {
          vec2 uv = v_texCoord;
          vec2 p = (uv - 0.5) * (u_resolution.x / u_resolution.y);
          
          // Deep Graphite Base
          vec3 color = vec3(0.02, 0.025, 0.03);
          
          // 1. Shifting Monitoring Grid
          vec2 gridUV = uv * 10.0 + u_time * 0.02;
          float grid = (smoothstep(0.0, 0.015, abs(fract(gridUV.x) - 0.5)) - 0.985) +
                       (smoothstep(0.0, 0.015, abs(fract(gridUV.y) - 0.5)) - 0.985);
          color += grid * 0.05;

          // 2. Network Topology: Lines, Nodes, and Packets
          for(float i = 0.0; i < 11.0; i++) {
              float t = u_time * (0.012 + i * 0.002);
              
              // Node Positions (dynamic & smooth)
              vec2 nA = vec2(noise(vec2(i * 3.14, t)), noise(vec2(t * 0.9 + i, i * 1.7)));
              vec2 nB = vec2(noise(vec2(i * 1.5 + 17.0, t * 0.75)), noise(vec2(t * 0.6 + i, i * 2.3 + 13.0)));
              
              // Scale to screen
              vec2 pa = (nA - 0.5) * 1.9;
              vec2 pb = (nB - 0.5) * 1.9;
              
              // Line math
              vec2 ba = pb - pa;
              vec2 p_pa = p - pa;
              float h = clamp(dot(p_pa, ba) / dot(ba, ba), 0.0, 1.0);
              float dist = length(p_pa - ba * h);
              
              // Thin cybernetic connections
              float line = smoothstep(0.004, 0.0, dist);
              float lineFade = sin(u_time * 0.6 + i * 1.5) * 0.4 + 0.6;
              color += line * vec3(0.0, 0.45, 0.75) * 0.18 * lineFade;

              // Moving packets on lines
              float packetPos = fract(u_time * 0.28 + i * 0.15);
              float packet = smoothstep(0.014, 0.0, length(p_pa - ba * packetPos));
              color += packet * vec3(0.0, 0.85, 1.0) * 0.75;
              
              // Node core
              float node = smoothstep(0.01, 0.0, length(p_pa));
              color += node * vec3(0.35, 0.8, 1.0) * 0.5;
          }

          // 3. Horizontal Cyber Scanning Lines
          float scan = fract(u_time * 0.06);
          float scanMask = smoothstep(scan, scan - 0.004, uv.y) * smoothstep(scan - 0.008, scan - 0.004, uv.y);
          color += scanMask * vec3(0.0, 0.9, 1.0) * 0.08;

          // 4. Ambient Holographic HUD Circles
          float hudCircle1 = smoothstep(0.004, 0.0, abs(length(p - vec2(0.35, -0.22)) - 0.35));
          color += hudCircle1 * 0.025 * vec3(0.0, 0.8, 1.0);

          float hudCircle2 = smoothstep(0.003, 0.0, abs(length(p - vec2(-0.45, 0.28)) - 0.22));
          color += hudCircle2 * 0.018 * vec3(0.0, 0.8, 1.0);

          // Dark border Vignette
          float vignette = 1.0 - length(uv - 0.5) * 1.4;
          color *= clamp(vignette, 0.0, 1.0);

          gl_FragColor = vec4(color, 1.0);
      }
    `;

    const createShader = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error("Shader compiles fail:", gl.getShaderInfoLog(shader));
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    };

    const vertexShader = createShader(gl.VERTEX_SHADER, vsSource);
    const fragmentShader = createShader(gl.FRAGMENT_SHADER, fsSource);
    if (!vertexShader || !fragmentShader) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Program linking fail:", gl.getProgramInfoLog(program));
      return;
    }

    const positionAttributeLocation = gl.getAttribLocation(program, "a_position");
    const resolutionUniformLocation = gl.getUniformLocation(program, "u_resolution");
    const timeUniformLocation = gl.getUniformLocation(program, "u_time");

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    const positions = [
      -1, -1,
       1, -1,
      -1,  1,
      -1,  1,
       1, -1,
       1,  1,
    ];
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.STATIC_DRAW);

    let frameId = 0;
    let isRunning = false;
    let isScrolling = false;
    let isPointerFine = window.matchMedia("(pointer: fine)").matches;
    let scrollResumeTimer = 0;
    let lastFrameAt = 0;
    const startTime = performance.now();

    const resizeCanvas = () => {
      const pixelRatio = Math.min(window.devicePixelRatio || 1, isPointerFine ? 1.15 : 0.9);
      const w = Math.max(1, Math.floor(canvas.clientWidth * pixelRatio));
      const h = Math.max(1, Math.floor(Math.min(canvas.clientHeight, window.innerHeight * 1.25) * pixelRatio));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
        gl.viewport(0, 0, w, h);
      }
    };

    const render = (now: number) => {
      if (!isRunning) return;

      const frameInterval = isScrolling ? 120 : isPointerFine ? 50 : 66;
      if (now - lastFrameAt < frameInterval) {
        frameId = requestAnimationFrame(render);
        return;
      }
      lastFrameAt = now;

      gl.clearColor(0.01, 0.012, 0.015, 1.0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      gl.useProgram(program);
      gl.enableVertexAttribArray(positionAttributeLocation);
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.vertexAttribPointer(positionAttributeLocation, 2, gl.FLOAT, false, 0, 0);

      gl.uniform2f(resolutionUniformLocation, canvas.width, canvas.height);
      gl.uniform1f(timeUniformLocation, (now - startTime) / 1000.0);

      gl.drawArrays(gl.TRIANGLES, 0, 6);
      frameId = requestAnimationFrame(render);
    };

    const startRenderLoop = () => {
      if (isRunning || document.hidden) return;
      isRunning = true;
      frameId = requestAnimationFrame(render);
    };

    const stopRenderLoop = () => {
      isRunning = false;
      cancelAnimationFrame(frameId);
    };

    const resizeHandler = () => {
      isPointerFine = window.matchMedia("(pointer: fine)").matches;
      resizeCanvas();
    };
    const scrollHandler = () => {
      isScrolling = true;
      window.clearTimeout(scrollResumeTimer);
      scrollResumeTimer = window.setTimeout(() => {
        isScrolling = false;
      }, 140);
    };
    const visibilityHandler = () => {
      if (document.hidden) {
        stopRenderLoop();
      } else {
        startRenderLoop();
      }
    };

    resizeCanvas();
    window.addEventListener("resize", resizeHandler);
    window.addEventListener("scroll", scrollHandler, { passive: true });
    document.addEventListener("visibilitychange", visibilityHandler);
    startRenderLoop();

    return () => {
      stopRenderLoop();
      window.clearTimeout(scrollResumeTimer);
      window.removeEventListener("resize", resizeHandler);
      window.removeEventListener("scroll", scrollHandler);
      document.removeEventListener("visibilitychange", visibilityHandler);
      gl.deleteBuffer(positionBuffer);
      gl.deleteProgram(program);
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-screen h-screen pointer-events-none z-0 opacity-60"
    />
  );
});

export default ShaderBackground;
