"""Project monocular facial depth bands into the selected semantic mask."""
import base64

import cv2
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import QhullError


GREEN = ((147, 255, 175), (101, 245, 148), (65, 220, 118),
         (42, 178, 94), (27, 143, 76), (19, 111, 60))


def create_mesh_detector(model):
    import mediapipe as mp

    vision = mp.tasks.vision
    options = vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.IMAGE,
        min_face_detection_confidence=.3,
        min_face_presence_confidence=.35,
    )
    return vision.FaceLandmarker.create_from_options(options)


def measure_landmarks(crop, detector):
    import mediapipe as mp

    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                      data=cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
    if not result.face_landmarks:
        return None
    return np.array([(point.x, point.y, point.z) for point in result.face_landmarks[0][:468]], dtype=np.float32)


def landmarks(crop, model):
    with create_mesh_detector(model) as detector:
        points = measure_landmarks(crop, detector)
    if points is None:
        raise ValueError("Depth bands could not be estimated. Try a clearer view of the selected face.")
    return points


def depth_bands(points, crop_size, projection, alpha):
    left, top, width, height = cv2.boundingRect(alpha)
    if not width or not height:
        raise ValueError("The selected face mask is empty.")
    crop_width, crop_height = crop_size
    y, x = np.mgrid[:crop_height, :crop_width].astype(np.float32)
    try:
        sample = LinearNDInterpolator(points[:, :2], points[:, 2], fill_value=np.nan)
        depth = sample(x/crop_width, y/crop_height).astype(np.float32)
    except QhullError:
        raise ValueError("Depth bands could not be estimated from this view.") from None
    known = np.isfinite(depth).astype(np.float32)
    inverse = projection.copy()
    inverse[:, 2] -= [left, top]
    # Project depth and its support together so undefined points never
    # contribute interpolated depth at the edge of the visible surface.
    support = cv2.warpAffine(known, inverse, (width, height))
    warped = cv2.warpAffine(np.nan_to_num(depth), inverse, (width, height))
    roi = alpha[top:top+height, left:left+width]
    valid = (roi > 0) & (support > .95)
    if not valid.any():
        raise ValueError("The estimated surface does not overlap the face mask.")
    warped[valid] /= support[valid]
    near, far = np.percentile(warped[valid], (3, 97))
    if far - near < 1e-5:
        raise ValueError("This frame does not provide enough relative depth to separate bands.")
    cuts = np.linspace(near, far, len(GREEN)+1)[1:-1]
    band = np.searchsorted(cuts, warped)
    result = []
    for index, rgb in enumerate(GREEN):
        layer = np.zeros((height, width, 4), dtype=np.uint8)
        layer[..., :3] = rgb[::-1]
        inside = valid & (band == index)
        layer[..., 3][inside] = np.rint(roi[inside] * .73).astype(np.uint8)
        _, png = cv2.imencode(".png", layer)
        result.append(base64.b64encode(png).decode("ascii"))
    return {"width":alpha.shape[1], "height":alpha.shape[0],
            "bounds":[left,top,width,height], "bands":result}
