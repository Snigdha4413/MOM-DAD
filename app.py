import io
import os

import cv2
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps

import ballpit
from hero import intro_html

st.set_page_config(page_title='Mom or Dad? | Best of Luck', page_icon='🎈', layout='centered', initial_sidebar_state='collapsed')

BASE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(BASE, *a)

# ---------------------------------------------------------------- load model (cached across reruns)
@st.cache_resource
def load_model():
    with np.load(P('model.npz')) as z:
        return {k: z[k] for k in z.files}


model = load_model()

# Where the eyes sit in a TSKinFace 64x64 crop (measured from the dataset's eye annotations):
EYE_MID_X, EYE_MID_Y = 32, 26     # point between the eyes
EYE_DIST = 22.25                  # pixels between the eyes
SQUASH_Y = 0.76                   # the dataset crops are squashed vertically

yy, xx = np.mgrid[0:64, 0:64] / 64
MASK = ((xx - 0.5) / 0.40) ** 2 + ((yy - 0.52) / 0.52) ** 2 <= 1


# ================================================================ STYLE  ("Best of Luck Nikki" look: teal + ball pit + marker fonts)
BALLS = ballpit.tile()

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600&family=Gochi+Hand&display=swap');
:root { --hand: 'Gochi Hand', 'Comic Sans MS', cursive; --sans: Fredoka, system-ui, sans-serif;
        --ink: #fff; --muted: #bfe3ee; --teal: #20c3a6; --yellow: #ffc83d; --red: #e7343c; --blue: #2c84e0;
        --line: rgba(255,255,255,.22); --glass: rgba(6,44,66,.62); }

/* ball-pit wallpaper, dimmed by a teal scrim so foreground content stays readable */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; color: var(--ink); font-family: var(--sans); }
.stApp { background: linear-gradient(rgba(8,50,74,.88), rgba(8,50,74,.92)), url(__BALLS__) !important; background-size: auto, 420px !important; background-attachment: fixed !important; }
.stApp:has(.hero-title) { background: linear-gradient(rgba(8,50,74,.66), rgba(8,50,74,.80)), url(__BALLS__) !important; background-size: auto, 420px !important; background-attachment: fixed !important; }
html, body { overflow-x: clip; }
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], footer, #MainMenu { display: none !important; }
.block-container { padding: 120px 16px 80px !important; max-width: 980px !important; }
.stApp, .stApp button, .stApp label, .stApp p, .stApp li { font-family: var(--sans); }

h1, h2, h3 { font-family: var(--hand) !important; font-weight: 400 !important; letter-spacing: .01em !important; color: var(--ink) !important; text-shadow: 0 2px 0 rgba(0,0,0,.25); }
h1 { font-size: clamp(34px, 5vw, 52px) !important; text-align: center; padding-top: 0 !important; }
h2, h3 { font-size: 30px !important; }
[data-testid="stCaptionContainer"], .stCaption, small { color: var(--muted) !important; }

/* ---------- floating pill nav ---------- */
.st-key-nav { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 999991; width: min(760px, calc(100% - 24px));
              padding: 7px 10px 7px 20px; border-radius: 999px; background: rgba(8,50,74,.72); border: 2px solid rgba(255,255,255,.28);
              backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); box-shadow: 0 8px 0 rgba(0,0,0,.22); }
.st-key-nav [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .5rem !important; align-items: center; }
.st-key-nav [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-nav .brand { font: 400 24px var(--hand); white-space: nowrap; color: var(--ink); }
.st-key-n_home button, .st-key-n_how button { background: transparent !important; border: none !important; box-shadow: none !important;
        color: var(--muted) !important; padding: 0 !important; min-height: 0 !important; font-size: 14px !important; width: auto !important; }
.st-key-n_home button:hover, .st-key-n_how button:hover { color: #fff !important; }
.st-key-n_start { display: flex; justify-content: flex-end; }
.st-key-n_start button { width: auto !important; padding: 6px 18px !important; }
@media (max-width: 640px) { .st-key-n_home, .st-key-n_how { display: none; } }

/* ---------- hero ---------- */
@keyframes rise { to { opacity: 1; transform: none; } }
.hero-title { display: block; width: min(760px, 100%); margin: 0 auto !important; text-align: center !important;
              font: 400 clamp(36px, 6vw, 68px)/1.08 var(--hand) !important; text-shadow: 0 3px 0 rgba(0,0,0,.3), 0 0 24px rgba(0,0,0,.35);
              opacity: 0; transform: translateY(14px); animation: rise .9s .1s cubic-bezier(.2,.7,.2,1) forwards; }
.hero-title em { font-style: normal; color: var(--yellow); }
.hero-sub { display: block; width: min(520px, 100%); margin: 14px auto 0 !important; text-align: center !important; color: var(--muted);
            font: 400 15px/1.55 var(--sans) !important; opacity: 0; animation: rise .9s .3s cubic-bezier(.2,.7,.2,1) forwards; }
/* intro: plays full screen on top of everything, then fades away to reveal the title page */
@keyframes rise2 { to { opacity: 1; transform: none; } }
@keyframes introOut { to { opacity: 0; visibility: hidden; pointer-events: none; } }
.st-key-hero_intro { position: fixed !important; inset: 0; z-index: 999995; width: 100vw !important; height: 100vh; margin: 0 !important;
                     background: linear-gradient(rgba(8,50,74,.66), rgba(8,50,74,.80)), url(__BALLS__); background-size: auto, 420px;
                     animation: introOut .6s 10.5s forwards; }          /* safety net: hides itself even if the intro can't signal */
.st-key-hero_intro * { max-width: none !important; }
.st-key-hero_intro .stElementContainer, .st-key-hero_intro iframe { width: 100% !important; height: 100vh !important; flex: 0 0 100vh !important; border: 0; }
html.intro-done .st-key-hero_intro { opacity: 0 !important; visibility: hidden !important; pointer-events: none !important;
                                     transition: opacity .6s, visibility 0s .6s; }
.st-key-hero_start { display: flex; justify-content: center; width: 100% !important; margin-top: 6px; }   /* full width, so the button can sit in the middle */
.st-key-hero_start .stButton { display: flex; justify-content: center; }

/* ---------- GET STARTED: the button sits on the ball pit ---------- */
.st-key-hero_start button[kind="primary"], .st-key-n_start button[kind="primary"], .st-key-n_start button {
    background: linear-gradient(rgba(6,40,60,.40), rgba(6,40,60,.40)), url(__BALLS__) center / 300px !important;
    color: #fff !important; border: 3px solid #fff !important; border-radius: 999px !important; font-weight: 600 !important;
    text-shadow: 0 2px 0 rgba(0,0,0,.55), 0 0 10px rgba(0,0,0,.6); box-shadow: 0 7px 0 #0a3a52, 0 14px 24px rgba(0,0,0,.35) !important;
    transition: transform .15s, box-shadow .15s, background-position .6s; }
.st-key-hero_start button { width: auto !important; padding: 14px 52px !important; min-height: 60px; }
.st-key-hero_start button p { font: 400 30px var(--hand) !important; }
.st-key-hero_start button:hover, .st-key-n_start button:hover { transform: translateY(-3px) scale(1.03); background-position: 0 0, 60px 40px !important; border-color: var(--yellow) !important; }
.st-key-hero_start button:active, .st-key-n_start button:active { transform: translateY(4px); box-shadow: 0 3px 0 #0a3a52 !important; }
.stApp button:focus-visible { outline: 3px solid var(--yellow) !important; outline-offset: 3px; }

/* ---------- widgets ---------- */
.stButton button, .stDownloadButton button { width: 100%; border-radius: 14px; background: var(--teal); color: #05302a; border: 2px solid #fff;
        padding: 12px 18px; font-weight: 600; box-shadow: 0 5px 0 rgba(0,0,0,.25); transition: all .15s; }
.stButton button:hover { background: #3fd9bd; color: #05302a; transform: translateY(-2px); }
.stButton button[kind="primary"] { background: var(--yellow); color: #4a2b00; }
.stButton button[kind="primary"]:hover { background: #ffd966; }
.stButton button:disabled { opacity: .45; }
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--glass); border: 2px solid var(--line) !important; border-radius: 20px; padding: 10px 8px; }
.st-key-nav [data-testid="stVerticalBlockBorderWrapper"] { background: transparent; border: none !important; padding: 0; }
[data-testid="stFileUploaderDropzone"], [data-testid="stCameraInput"] { background: rgba(255,255,255,.08); border: 2px dashed rgba(255,255,255,.4); border-radius: 16px; }
[data-testid="stAlert"] { background: var(--glass) !important; border: 2px solid var(--line); border-radius: 16px; }
[data-testid="stAlertContainer"], [data-testid="stAlert"] p { background: transparent !important; color: var(--ink) !important; }
[data-baseweb="tab-list"] { gap: 6px; } [data-baseweb="tab-highlight"] { background: var(--yellow) !important; }
[data-testid="stProgress"] div[role="progressbar"] > div { background: var(--yellow) !important; }
[data-testid="stExpander"] { background: var(--glass); border: 2px solid var(--line); border-radius: 16px; }
.steps { display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; margin-bottom: 26px; font-size: 13px; }
.steps span { padding: 7px 16px; border-radius: 99px; border: 2px solid var(--line); color: var(--muted); }
.steps span.on { color: #4a2b00; background: var(--yellow); border-color: #fff; font-weight: 600; }

/* ---------- tablets & phones ---------- */
@media (max-width: 768px) { .block-container { padding: 104px 12px 64px !important; } }
@media (max-width: 480px) { .st-key-hero_start button { padding: 12px 38px !important; } .st-key-hero_start button p { font-size: 26px !important; }
                            .st-key-nav .brand { font-size: 21px; } }
@media (prefers-reduced-motion: reduce) { .hero-title, .hero-sub { animation: none; opacity: 1; transform: none; } .stApp button { transition: none !important; } }
</style>
""".replace('__BALLS__', BALLS)
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data
def intro_doc():
    return intro_html(BASE)           # hero_intro.html: dad, mom, kids frames + hanging sign


# ================================================================ face pipeline (unchanged logic)
def align(file, who):
    img = np.array(ImageOps.exif_transpose(Image.open(file)).convert('RGB'))
    scale = min(1.0, 1024 / max(img.shape[:2]))                  # detect on a smaller copy (faster)
    small = cv2.resize(img, None, fx=scale, fy=scale)
    detector = cv2.FaceDetectorYN.create(P('yunet.onnx'), '', (small.shape[1], small.shape[0]), 0.6)
    _, faces = detector.detect(cv2.cvtColor(small, cv2.COLOR_RGB2BGR))
    if faces is None:
        st.error(f'No face found in the {who} photo. Try a clear, front-facing photo.')
        st.stop()

    face = max(faces, key=lambda f: f[2] * f[3]) / scale          # biggest face, back to full size
    left, right = sorted([face[4:6], face[6:8]], key=lambda p: p[0])

    # YuNet's eye points sit a little higher and wider than the dataset's; correct for that
    axis = right - left
    dist = np.linalg.norm(axis) / 1.068
    axis = axis / np.linalg.norm(axis)
    down = np.array([-axis[1], axis[0]])
    mid = (left + right) / 2 + (0.047 * axis + 0.050 * down) * dist

    # rotate so the eyes are level, scale to the right eye distance, squash, move eyes into place
    angle = -np.arctan2(axis[1], axis[0])
    rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]) * (EYE_DIST / dist)
    A = np.diag([1, SQUASH_Y]) @ rot
    b = np.array([EYE_MID_X, EYE_MID_Y]) - A @ mid
    return cv2.warpAffine(img, np.hstack([A, b[:, None]]), (64, 64), flags=cv2.INTER_AREA,
                          borderMode=cv2.BORDER_REPLICATE)


def prep(img):
    g = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)).astype(float)
    g[~MASK] = 128                                                # background -> plain grey
    return g.reshape(-1)


def region(x, box):
    top, bottom, left, right = box
    return x.reshape(64, 64)[top:bottom, left:right].reshape(-1)


def to_space(x, name):
    return (x - model[name + '_mean']) @ model[name + '_W']       # whitened PCA + removals, in one matrix


def cos(a, b):
    return a @ b / (np.linalg.norm(a) * np.linalg.norm(b))


def dad_percentile(zf, zm, zc, ref):
    g = cos(zc, zf) - cos(zc, zm)                                 # > 0 means more like dad
    return np.mean(ref < g)                                       # rank among same-sex children


def big(img):
    return cv2.resize(img, (192, 192), interpolation=cv2.INTER_CUBIC)


# ================================================================ page state
S = st.session_state
S.setdefault('step', 'home'); S.setdefault('kids', []); S.setdefault('mode', 'upload')
EXAMPLE = [P('examples', n) for n in ('father.jpg', 'mother.jpg', 'child.jpg')]
TYPES = ['jpg', 'jpeg', 'png']


def go(step): S['step'] = step
def pick(mode): S.update(mode=mode, step='photos')
def reset(): S.update(step='mode', kids=[], data=None, ex=False)
def rd(x): return x.getvalue() if hasattr(x, 'getvalue') else open(x, 'rb').read()


def stepper(n):
    tags = ''.join(f'<span class="{"on" if i <= n else ""}">{i + 1} · {t}</span>' for i, t in enumerate(['Method', 'Photos', 'Analysis']))
    st.markdown(f'<div class="steps">{tags}</div>', unsafe_allow_html=True)


# ================================================================ floating nav
with st.container(key='nav'):
    c_brand, c_home, c_how, c_cta = st.columns([2.2, 1, 1.4, 1.6], vertical_alignment='center')
    c_brand.markdown('<span class="brand">Mom or Dad?</span>', unsafe_allow_html=True)
    c_home.button('Home', key='n_home', on_click=go, args=('home',))
    c_how.button('How it works', key='n_how', on_click=go, args=('mode',))
    if S['step'] == 'home':
        c_cta.button('Get started', key='n_start', on_click=go, args=('mode',))
active = 'n_home' if S['step'] == 'home' else 'n_how'
st.markdown(f'<style>.st-key-{active} button {{ color:#fff !important; font-weight:500 !important; }}</style>', unsafe_allow_html=True)


def analyse(f, m, c, son):
    """Whole-face verdict, feature map and relatedness for one child. Returns dad percentile (or None)."""
    sex, kids = ('son', 'sons') if son else ('daughter', 'daughters')
    zf, zm, zc = to_space(prep(f), 'face'), to_space(prep(m), 'face'), to_space(prep(c), 'face')
    if cos(zf, zm) > 0.99 or cos(zc, zf) > 0.99 or cos(zc, zm) > 0.99:
        st.warning('Two of the photos look identical. Use three different people for a real result.')
        return None
    p = dad_percentile(zf, zm, zc, model[f'g_{sex}'])
    st.image([big(f), big(m), big(c)], caption=['Father', 'Mother', 'Child'], width=150)
    st.subheader('Verdict')
    if 0.4 <= p <= 0.6:
        st.info(f'**An even mix.** More like dad than {p:.0%} of {kids} in our data.')
    elif p > 0.6:
        st.success(f'**Looks more like DAD.** More like dad than {p:.0%} of {kids} in our data.')
    else:
        st.success(f'**Looks more like MUM.** More like mum than {1 - p:.0%} of {kids} in our data.')
    st.progress(float(p), text=f'Mum ◀ {1 - p:.0%} | {p:.0%} ▶ Dad')

    st.subheader('Feature by feature')
    canvas, lines = cv2.resize(c, (256, 256), interpolation=cv2.INTER_CUBIC), []
    for i, (name, box) in enumerate(zip(model['region_names'], model['region_boxes'])):
        key = f'r{i}'
        zf, zm, zc = (to_space(region(prep(x), box), key) for x in (f, m, c))
        q = dad_percentile(zf, zm, zc, model[f'{key}_g_{sex}'])
        colour = np.array([42, 120, 214]) if q > 0.5 else np.array([232, 123, 164])   # blue = dad, pink = mum
        strength = min(1.0, abs(q - 0.5) * 2.4)
        top, bottom, left, right = (int(v) * 4 for v in box)
        patch = canvas[top:bottom, left:right].astype(float)
        canvas[top:bottom, left:right] = (patch * (1 - 0.6 * strength) + colour * 0.6 * strength).astype(np.uint8)
        lines.append(f'**{name}**: like {"dad" if q > 0.5 else "mum"} (more than {max(q, 1 - q):.0%} of {kids})')
    a, b = st.columns([1, 1.3])
    a.image(canvas, caption='Blue = dad, pink = mum, stronger colour = stronger lean', width=256)
    b.markdown('\n\n'.join(lines))

    st.subheader('Do they look related at all?')
    zc, zp = to_space(prep(c), 'face'), (to_space(prep(f), 'face') + to_space(prep(m), 'face')) / 2
    s = cos(zc, zp)
    st.write(f"Looks more like this couple than **{np.mean(model['sim_stranger'] < s):.0%}** of random couples, "
             f"and more than {np.mean(model['sim_own'] < s):.0%} of real children resemble their own parents.")
    return p


# ================================================================ pages
# ---- landing page: catchy phrase + intro (dad, mom, kids frames, then the hanging sign) on the ball pit
if S['step'] == 'home':
    st.markdown('<div class="hero-title">Mom\'s smile or Dad\'s? <em>Best of luck</em> finding out!</div>'
                '<div class="hero-sub">Our face-space model has studied 776 real families. Add your photos and see who '
                'each sibling takes after.</div>', unsafe_allow_html=True)
    if not S.get('intro_seen'):                    # the intro plays once per visit, before the title page
        S['intro_seen'] = True
        st.markdown('<style>.hero-title { animation-delay: 10.6s !important; } .hero-sub { animation-delay: 10.8s !important; }'
                    'html.intro-done .hero-title { animation: rise2 .9s .35s cubic-bezier(.2,.7,.2,1) forwards !important; }'
                    'html.intro-done .hero-sub { animation: rise2 .9s .55s cubic-bezier(.2,.7,.2,1) forwards !important; }</style>',
                    unsafe_allow_html=True)
        with st.container(key='hero_intro'):
            components.html(intro_doc(), height=600)
    st.button('Get started', key='hero_start', type='primary', on_click=go, args=('mode',))

# ---- step 1: how do you want to add photos?
elif S['step'] == 'mode':
    stepper(0)
    st.title('How would you like to add your photos?')
    st.caption('Pick a method to begin.')
    a, b = st.columns(2)
    with a.container(border=True):
        st.subheader('Upload photos'); st.write('Choose pictures from your device. You can add several siblings at once.')
        st.button('Upload from device', on_click=pick, args=('upload',))
    with b.container(border=True):
        st.subheader('Live camera'); st.write('Take the photos right now with your webcam or phone camera.')
        st.button('Open camera', on_click=pick, args=('camera',))

# ---- step 2: the photos
elif S['step'] == 'photos':
    stepper(1)
    cam = S['mode'] == 'camera'
    st.title('Add the family')
    st.caption('Tip: clear, front-facing photos with good light work best.')
    one = (lambda label, key: st.camera_input(label, key=key)) if cam else (lambda label, key: st.file_uploader(label, type=TYPES, key=key))
    c1, c2 = st.columns(2)
    with c1: f = one('Father', 'f')
    with c2: m = one('Mother', 'm')

    st.subheader('Children')
    st.caption('Add one child or several siblings. Each one gets their own result.')
    kids = []
    if cam:
        shot = st.camera_input('Take a child photo', key=f'cam{len(S["kids"])}')
        if shot and st.button('Add this child'):
            S['kids'].append(shot.getvalue()); st.rerun()
        kids += [io.BytesIO(k) for k in S['kids']]
    kids += st.file_uploader('Upload children' if not cam else 'Or upload from device', type=TYPES, accept_multiple_files=True, key='ku')

    if all(os.path.exists(p) for p in EXAMPLE):
        st.button('Try an example family', on_click=lambda: S.update(ex=True))
    if S.get('ex') and not (f or m or kids):
        f, m, kids = EXAMPLE[0], EXAMPLE[1], [EXAMPLE[2]]

    sexes = []
    for i, k in enumerate(kids):
        x, y = st.columns([1, 5])
        x.image(k, width=80)
        sexes.append(y.radio(f'Child {i + 1} is a', ['Son', 'Daughter'], horizontal=True, key=f'sex{i}') == 'Son')

    back, nxt = st.columns(2)
    back.button('← Back', on_click=lambda: S.update(step='mode'))
    ready = bool(f and m and kids)
    if nxt.button('Analyze family', type='primary', disabled=not ready):
        S['data'] = {'f': rd(f), 'm': rd(m), 'kids': [(rd(k), s) for k, s in zip(kids, sexes)]}
        S['step'] = 'results'; st.rerun()
    if not ready:
        st.caption('Add a father, a mother and at least one child to continue.')

# ---- step 3: analysis
else:
    stepper(2)
    st.title('Your results')
    d = S['data']
    f, m = align(io.BytesIO(d['f']), 'father'), align(io.BytesIO(d['m']), 'mother')
    summary, ps = st.container(), []
    tabs = st.tabs([f'Child {i + 1}' for i in range(len(d['kids']))])
    for i, (tab, (raw, son)) in enumerate(zip(tabs, d['kids'])):
        with tab:
            p = analyse(f, m, align(io.BytesIO(raw), f'child {i + 1}'), son)
            if p is not None: ps.append(p)
    if len(ps) > 1:
        avg = float(np.mean(ps))
        who = 'dad' if avg > 0.5 else 'mum'
        summary.info(f'**Family overview:** across {len(ps)} children the lean is toward **{who}** '
                     f'(average {max(avg, 1 - avg):.0%} rank). Open each tab for the individual result.')
    st.button('Start over', on_click=reset)
    st.caption('Demo, not a genetic test. Trained on TSKinFace (776 families). Each verdict is ranked against '
               'children of the same sex, so a son is not called "like dad" just for being a boy.')
