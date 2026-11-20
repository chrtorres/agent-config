import {
  HalfFloatType, Vector2, WebGLRenderTarget,
} from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";

export const GRAPHICS_TIERS = ["balanced", "cinematic", "ultra-4k"];

export function graphicsScale(width, height, screenRatio, tier, hardwareLimit) {
  const ultra = tier === "ultra-4k";
  const high = ultra || tier === "cinematic";
  const cap = high ? [3840, 2160] : [2560, 1440];
  const maximum = Math.min(cap[0] / width, cap[1] / height, hardwareLimit / Math.max(width, height));
  return Math.min(maximum, ultra ? maximum : Math.min(screenRatio, high ? 2 : 1.5));
}

export function createPresentation(renderer, scene, camera) {
  const gl = renderer.getContext();
  const limit = Math.min(renderer.capabilities.maxTextureSize, gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),
    ...gl.getParameter(gl.MAX_VIEWPORT_DIMS));
  const hdr = renderer.extensions.has("EXT_color_buffer_float");
  const buffers = hdr ? new WebGLRenderTarget(1, 1, { type: HalfFloatType }) : null;
  const composer = buffers ? new EffectComposer(renderer, buffers) : null;
  const bloom = new UnrealBloomPass(new Vector2(1, 1), .22, .65, 1.05);
  const antialias = new ShaderPass(FXAAShader);
  composer?.addPass(new RenderPass(scene, camera));
  composer?.addPass(bloom);
  composer?.addPass(new OutputPass());
  // FXAA reads perceptual contrast. Run it after the linear-to-display conversion.
  composer?.addPass(antialias);

  const drawing = new Vector2();
  let pipelineWidth = 0, pipelineHeight = 0;
  let usePostProcessing = false;
  return {
    resize(width, height, screenRatio, tier) {
      // An 8-bit intermediate would clip the scene before the ACES transform.
      usePostProcessing = hdr && tier !== "balanced";
      const scale = graphicsScale(width, height, screenRatio, tier, limit);
      renderer.setDrawingBufferSize(width, height, scale);
      renderer.getDrawingBufferSize(drawing);
      if (!usePostProcessing && pipelineWidth) {
        // A player switching back to Balanced can reclaim the UHD post targets immediately.
        composer.setSize(1, 1);
        pipelineWidth = pipelineHeight = 0;
      } else if (usePostProcessing && (drawing.x !== pipelineWidth || drawing.y !== pipelineHeight)) {
        // The composer uses physical pixels so the antialias kernel stays one texel wide at UHD.
        pipelineWidth = drawing.x;
        pipelineHeight = drawing.y;
        composer.setSize(pipelineWidth, pipelineHeight);
        antialias.uniforms.resolution.value.set(1 / pipelineWidth, 1 / pipelineHeight);
      }
    },
    render(dt) {
      if (usePostProcessing) composer.render(dt);
      else renderer.render(scene, camera);
    },
    get resolution() {
      return {
        width: drawing.x, height: drawing.y, antiAlias: usePostProcessing ? "fxaa" : "native",
        postWidth: pipelineWidth,
        postHeight: pipelineHeight,
      };
    },
  };
}
