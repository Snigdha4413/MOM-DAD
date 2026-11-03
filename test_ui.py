"""Run with:  pytest tests/ -q      (needs model.npz + yunet.onnx next to app.py, like the real app)"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from hero import CAST, build_slides, slider_html


def fresh():
    return AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60).run()


def test_home_renders_without_errors():
    at = fresh()
    assert not at.exception
    assert any(b.key == 'hero_start' for b in at.button)


def test_get_started_opens_method_step():
    at = fresh()
    next(b for b in at.button if b.key == 'hero_start').click().run()
    assert at.session_state['step'] == 'mode'


def test_slider_has_three_to_four_slides():
    assert 3 <= len(build_slides(str(ROOT))) <= 4 == len(CAST)


def test_slider_is_responsive_and_accessible():
    html = slider_html(str(ROOT))
    assert '@container' in html and 'viewport' in html          # adapts to desktop/tablet/phone
    assert 'prefers-reduced-motion' in html                     # honours motion settings
    assert 'aria-label' in html and 'pointerup' in html         # labelled controls + swipe


def test_feedback_form_saves_a_row():
    fb = ROOT / 'feedback.jsonl'
    before = fb.read_text(encoding='utf-8') if fb.exists() else None
    try:
        at = fresh()
        at.text_area[0].input('love the ball pit')
        next(b for b in at.button if b.label == 'Send feedback').click().run()
        assert 'love the ball pit' in fb.read_text(encoding='utf-8').splitlines()[-1]
    finally:                                                     # leave real feedback untouched
        fb.unlink(missing_ok=True)
        if before is not None:
            fb.write_text(before, encoding='utf-8')
