"""
HC-XCDSS Test Suite: Pre-Inference Chest X-Ray Validation & OOD Safety Gate
"""

import sys
import shutil
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "src" / "inference"))

from validator import xray_validator, ChestXRayValidator
from service import XRayInferenceService


def test_1_real_frontal_xray_accepted():
    real_path = PROJECT_ROOT / "outputs" / "analyses" / "08a3cfaf3062" / "view1_frontal.jpg"
    is_valid, reason, details = xray_validator.validate(real_path, view="Frontal")
    assert is_valid is True, f"Real frontal X-ray should be accepted: {reason}"
    assert details["passed_layer1_file"] is True
    assert details["passed_layer2_radiometric"] is True
    assert details["passed_layer3_domain"] is True


def test_2_real_lateral_xray_accepted():
    real_path = PROJECT_ROOT / "outputs" / "analyses" / "08a3cfaf3062" / "view1_frontal.jpg"
    is_valid, reason, details = xray_validator.validate(real_path, view="Lateral")
    assert is_valid is True, f"Real lateral projection should be accepted: {reason}"


def test_3_car_photograph_rejected(tmp_path):
    car_path = tmp_path / "car.jpg"
    car_img = Image.new("RGB", (450, 320), color=(135, 206, 235))
    d = ImageDraw.Draw(car_img)
    d.rectangle([0, 160, 450, 320], fill=(60, 60, 60))
    d.rectangle([80, 110, 370, 230], fill=(220, 20, 60))
    d.ellipse([110, 200, 170, 260], fill=(10, 10, 10))
    d.ellipse([280, 200, 340, 260], fill=(10, 10, 10))
    car_img.save(car_path)

    is_valid, reason, details = xray_validator.validate(car_path, view="Frontal")
    assert is_valid is False
    assert "photographic" in reason or "out-of-domain" in reason


def test_4_nature_photograph_rejected(tmp_path):
    nature_path = tmp_path / "forest.jpg"
    nature_img = Image.new("RGB", (400, 300), color=(34, 139, 34))
    d = ImageDraw.Draw(nature_img)
    d.rectangle([0, 0, 400, 120], fill=(100, 149, 237))
    nature_img.save(nature_path)

    is_valid, reason, details = xray_validator.validate(nature_path, view="Frontal")
    assert is_valid is False


def test_5_website_screenshot_rejected(tmp_path):
    doc_path = tmp_path / "site.png"
    doc_img = Image.new("RGB", (400, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(doc_img)
    d.rectangle([20, 20, 380, 60], fill=(0, 51, 102))
    for y in range(80, 280, 18):
        d.line([(30, y), (370, y)], fill=(180, 180, 180), width=3)
    doc_img.save(doc_path)

    is_valid, reason, details = xray_validator.validate(doc_path, view="Frontal")
    assert is_valid is False


def test_6_random_graphic_logo_rejected(tmp_path):
    logo_path = tmp_path / "logo.png"
    logo_img = Image.new("L", (300, 300), color=255)
    d = ImageDraw.Draw(logo_img)
    d.rectangle([40, 40, 260, 260], fill=0)
    d.ellipse([80, 80, 220, 220], fill=255)
    logo_img.save(logo_path)

    is_valid, reason, details = xray_validator.validate(logo_path, view="Frontal")
    assert is_valid is False


def test_7_brain_mri_rejected(tmp_path):
    mri_path = tmp_path / "brain_mri.jpg"
    mri_img = Image.new("L", (400, 400), color=0)
    d = ImageDraw.Draw(mri_img)
    d.ellipse([80, 50, 320, 350], fill=120)
    d.ellipse([120, 90, 280, 310], fill=180)
    d.ellipse([170, 160, 230, 240], fill=40)
    mri_img.save(mri_path)

    is_valid, reason, details = xray_validator.validate(mri_path, view="Frontal")
    assert is_valid is False


def test_8_corrupted_image_rejected():
    corrupt_bytes = b"NOT_A_VALID_IMAGE_BYTES"
    is_valid, reason, details = xray_validator.validate(corrupt_bytes, view="Frontal")
    assert is_valid is False


def test_9_tiny_image_rejected(tmp_path):
    tiny_path = tmp_path / "tiny.png"
    Image.new("L", (30, 30), color=128).save(tiny_path)
    is_valid, reason, details = xray_validator.validate(tiny_path, view="Frontal")
    assert is_valid is False


def test_10_service_interception_prevents_inference(tmp_path):
    car_path = tmp_path / "car.jpg"
    Image.new("RGB", (300, 300), color=(255, 0, 0)).save(car_path)

    service = XRayInferenceService()
    try:
        service.analyze(car_path, view="Frontal")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Input domain validation failed" in str(e)


def test_11_external_high_res_xray_accepted():
    external_path = PROJECT_ROOT / "external_test" / "images" / "atelectasis_neg_01.jpg"
    if external_path.exists():
        is_valid, reason, details = xray_validator.validate(external_path, view="Frontal")
        assert is_valid is True, f"External high-resolution X-ray should be accepted: {reason}"
        assert details["passed_layer1_file"] is True
        assert details["passed_layer2_radiometric"] is True
        assert details["passed_layer3_domain"] is True


if __name__ == "__main__":
    print("Running validation tests...")
    test_1_real_frontal_xray_accepted()
    test_2_real_lateral_xray_accepted()
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        test_3_car_photograph_rejected(p)
        test_4_nature_photograph_rejected(p)
        test_5_website_screenshot_rejected(p)
        test_6_random_graphic_logo_rejected(p)
        test_7_brain_mri_rejected(p)
        test_8_corrupted_image_rejected()
        test_9_tiny_image_rejected(p)
        test_10_service_interception_prevents_inference(p)
    test_11_external_high_res_xray_accepted()
    print("All tests passed successfully!")
