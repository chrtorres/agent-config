# Cinematic presentation for a playable browser scene

Apply this procedure to a working game when upgrading visual fidelity, adding an internal render-resolution option, or preparing a gameplay reel. Start with [playable 3D regression and delivery](playable-3d.md) and use [the browser reel workflow](../../3d-modeling/references/browser-gameplay-reel.md) for media.

## Integrate and inspect

1. Capture representative views before changing the scene. Define repeatable input and camera paths for motion checks. Review silhouettes, near and far atmosphere, material response, and time-critical action effects at gameplay distance. Fix geometry, shading or compositing at the source of each harsh edge. Test high-contrast effects during motion against the actual level lighting.
2. Separate camera easing and reduced-motion presentation from simulation and camera input. Use frame-rate-independent easing for nonessential changes in framing. Verify immediate steering, look limits, collision, and event timing. Preserve third-person visibility, existing controller mappings, the save schema, and the preview origin when these are part of the product contract.
3. Set a drawing-buffer pixel budget independently of CSS size and device pixel ratio. Preserve aspect ratio and cap both axes against texture, renderbuffer and viewport limits. In a UHD preset, explicitly verify 3840 × 2160 at 16:9 on a supported GPU, including on a smaller window. Distinguish internal resolution, the encoded reel and physical display resolution in the handoff. Include a lower-cost default and measure performance separately if making a frame-rate claim.
4. In an HDR path, keep linear values in half-float intermediate targets. Apply bloom and grading before tone mapping and output conversion. For FXAA, use display-referred contrast after conversion and set its reciprocal pixel size from the actual buffer. Probe render-target support. If a needed HDR target is unavailable, use direct tone-mapped rendering to retain highlight detail. Shrink or dispose inactive post-process targets when switching to an inexpensive preset. Size them again when returning to the higher preset.
5. Build once and use that candidate for local review, production regression, and UAT. Check the rendered baseline, higher preset, buffer and target dimensions, resizing, return to the cheaper preset, and fallback without HDR. Exercise highlights and key gameplay effect states in real scenes. Check settled pixels and screenshots alongside diagnostic state and console errors. Report the observed rendering backend. Keep fixture/controller injection in fresh browser contexts. Hands-on pad acceptance includes activation, look, movement, and reconnect on the intended browser.
6. If asked for one UAT instance, identify stale windows and listeners by app ownership before closing them. Leave unrelated windows and services alone. Launch the exact tested production bundle on the intended save origin. Verify the served bundle, URL, live window and sole app listener. Record the build identity and tested versus pending acceptance.

## Isolated reproduction

Copy the [playable fixture](../assets/playable-3d) using the [existing setup](playable-3d.md#reproduce-the-synthetic-checkpoint-fixture). With its locked dependencies and browser installed, run the unit and production build checks, then:

```sh
CAPTURE_REEL=uhd BROWSER_GPU=1 npm run smoke -- <fresh-evidence-directory>
```

This exercises the ordinary keyboard, synthetic pad, storage and rendered pose checks first. The optional capture then verifies HDR and a deliberately missing float extension in fresh contexts, confirms the real UHD drawing buffer and release of high-resolution post targets, and steps two seconds of motion through the app's input and render loop. The destination includes a frame manifest, renderer identities and native-size PNGs. On supported software renderers, omit the hardware request and use `CAPTURE_REEL=1` for a 960 × 540 sequence plus the UHD still checks. The fixture uses a simple grid, synthetic character and beacon. It demonstrates resolution, rendering fallback and capture mechanics. Artistic fidelity and physical-device operation require the actual application and hardware.

See [capture comparison and resource disposition](cinematic-capture-provenance.md).
