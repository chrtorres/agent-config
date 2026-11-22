# Localized photo face swap

Use this workflow for two still photos. The source supplies the facial features. The target supplies the composition and the face placement. Deliver a lossless composite, a face mask, a same-scale comparison and a reproducibility report in the task’s version directory. The [Python example](../assets/photo-face-swap/) runs locally and accepts caller-supplied paths.

## Production and review

1. Define which face to change and whether to retain the target’s expression or transfer the source’s. Record oriented dimensions, the intended edit region and the visual acceptance criteria before processing. If multiple faces are detected, confirm the selected subject and provide a zero-based index from left to right.
2. Normalize EXIF orientation. Detect both eyes, the nose and both mouth corners. Use a similarity transform to align the points to the recognition and swap model templates. Generate a model-only baseline with the source identity vector and the aligned target crop. Check feature placement and expression before deciding whether to blend source texture. [FaceFusion alignment templates](https://github.com/facefusion/facefusion/blob/decc6c9d8f8e014878624452c6e8fe208726b4ec/facefusion/face_helper.py), [FaceFusion swap implementation](https://github.com/facefusion/facefusion/blob/decc6c9d8f8e014878624452c6e8fe208726b4ec/facefusion/processors/modules/face_swapper/core.py)
3. Build a semantic mask of the target’s facial region and feather inward. For a compatible pose where the source expression or texture matters, align both crops at a higher resolution and blend the photographed details inside the mask intersection. Estimate broad lighting corrections in CIELAB using face pixels. Inspect possible double edges at brows, lips and facial hair. Use the baseline when it better matches the requested expression or avoids misaligned detail. [FaceFusion face parser reference](https://github.com/facefusion/facefusion/blob/decc6c9d8f8e014878624452c6e8fe208726b4ec/facefusion/face_masker.py)
4. Map the edited crop and mask back to the target, apply alpha against a copy of its decoded pixels and save a PNG with the target color profile. The example was verified with sRGB inputs. Inspect embedded profiles and adapt the color conversion when inputs use different color spaces. Reopen the saved PNG and verify its dimensions, a positive number of changed pixels and zero decoded RGB changes where mask alpha is zero. Check that hair, ears, neck and other protected regions lie outside the active mask.
5. Make source reference, original and composite panels. Use identical crops at native pixel scale for the latter two. Inspect the entire output and use browser zoom to inspect the aligned features and blend boundary. When the user expects a test window, open the exact comparison in a visible desktop browser and confirm the image is actually visible before reporting it open. A headless render can verify the image loads. If desktop access is unavailable, provide the local file link and record the headless check. A static PNG can use the browser’s local file viewer.
6. Reproduce the run from an isolated copy with pinned dependencies and checksummed weights. Record commands, runtime, selected variant, mask statistics, artifact hashes and observed visual limits in the task report. Pixel preservation outside the mask and repeatability are measurable. A claimed likeness percentage additionally needs an agreed metric and independent ground truth for the intended pose and lighting. Keep private review files in the authorized task directory.

## Run the Python example

Copy [the example directory](../assets/photo-face-swap/) to the current version directory or a fresh reproduction workspace. It uses Python 3.10 and pinned OpenCV, NumPy, Pillow and ONNX Runtime CPU dependencies. First setup needs network access and about 602 MiB of model weights. The downloader verifies file digests for both fresh and cached copies. It contacts the public model sources. Image paths are used by the local editor.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B fetch_models.py
.venv/bin/python -B face_swap.py --source "<source-image>" --target "<target-image>" --output-dir composite
.venv/bin/python -B open_review.py composite
```

Use a new directory for each variant. Add `--model-only` for the target-conditioned baseline, and `--source-index` or `--target-index` for explicit face selection. `--models <model-directory>` lets the downloader and editor share a separate weight cache. The desktop launcher uses Python’s browser discovery and accepts `--browser <browser-name>` if needed. Confirm the named image in the actual window after launching.

| Output | Use |
| --- | --- |
| `face-swap.png` | Full-resolution composite |
| `face-mask.png` | Output-coordinate alpha, with zero marking exactly preserved pixels |
| `comparison.png` | Source reference and same-scale target crops |
| `verification.json` | Detected face counts, target landmark pixels, mask bounds, pixel counts, variant and PNG digest |

For an independent check with fictional portraits generated from Python, run the smoke test below. It uses real model inference, outputs both variants, checks the original target hash and four reproduced artifact hashes, and exercises missing inputs and invalid face selection. Inspect the generated comparison through the same launcher.

```bash
.venv/bin/python -B smoke.py --work-dir "<new-smoke-directory>"
.venv/bin/python -B open_review.py "<new-smoke-directory>/first"
```

## Capture and provenance

The originating task used a locally supplied FaceFusion tutorial to learn setup, source and target selection, and preview. Its model-only result was compared against a color-adjusted source-texture variant. The source-texture result carried the source eye shape and smile more clearly. A follow-up asked where the test window was after a headless check. The exact comparison was then opened in a visible Chrome window and confirmed by its window title. The captured workflow includes that desktop handoff. The visible test window confirms access to the review image. Likeness and blend quality still require inspection.

The factors below score prior coverage of outcome, inputs, procedure, resources and validation in that order, weighted 25/15/35/15/10. The user explicitly requested both existing skills be extended. Both now point to one optional workflow owned by full-stack-app-creation.

| Candidate | Factors | Score | Existing coverage and limits |
| --- | --- | ---: | --- |
| [3d-modeling](../../3d-modeling/SKILL.md) | 0.25 / 0.25 / 0.5 / 0 / 0.5 | 32.5% | Photo landmarks, versioned review and independent fidelity evidence. Its footage masks address motion and its fixtures lack the still-face pipeline. |
| [full-stack-app-creation](../SKILL.md) | 0.5 / 0.25 / 0.5 / 0 / 0.75 | 41.25% | Runnable workflows, isolated reproduction and browser artifact verification. It lacked the two-portrait contract, inference and a visible PNG handoff. |
| [product-refinement](../../product-refinement/SKILL.md) | 0.5 / 0.25 / 0.5 / 0 / 0.5 | 38.75% | Baseline comparison, isolated regression and artifact hashes. Its templates lack the editing algorithm and image-specific checks. |

| Resource | Disposition |
| --- | --- |
| CLI, download helper and dependency pins | Bundled. Caller supplies source, target, output and optional model cache. |
| Browser launcher, fixture generator and smoke test | Bundled Python. The fixture draws fictional faces without external image assets. Use an installed browser for the visible review. |
| Model weights | Regenerated by download using immutable revisions, release coordinates and digests in the helper. YuNet is MIT. The FaceFusion model metadata identifies ArcFace as non-commercial, HyperSwap as ResearchRAIL, and BiSeNet ResNet-18 as MIT. Consult the published terms for the intended use. [YuNet license](https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/LICENSE), [ArcFace metadata](https://github.com/facefusion/facefusion/blob/decc6c9d8f8e014878624452c6e8fe208726b4ec/facefusion/face_recognizer.py), [HyperSwap license](https://github.com/facefusion/facefusion-labs/blob/master/hyperswap/LICENSE.md), [BiSeNet metadata](https://github.com/facefusion/facefusion/blob/decc6c9d8f8e014878624452c6e8fe208726b4ec/facefusion/face_masker.py) |
| Tutorial, original photos, landmarks, renders, screenshots and run logs | Left in the originating task or its temporary review storage. The synthetic runner regenerates comparable artifacts. User paths, names, image data and browser executable paths are absent from the shared files. |
