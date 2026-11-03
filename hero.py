import base64
import json
import os

MAKERS = ['Alisha Rao', 'Sanaz Katpitia', 'Snigdha Mishra']

# the three picture frames, in the order the camera visits them: (label, example photo, frame colour)
# the big family frame at the end uses examples/family.jpg if it exists, otherwise an illustrated family
FAMILY = [
    ('Dad', 'father.jpg', '#6b4423'),
    ('Mom', 'mother.jpg', '#e0457b'),
    ('The kids', 'child.jpg', '#8cc63f'),
]


def photo(base_dir, file_name):
    """The example photo as a data URL (the intro runs in its own frame, so it can't load files by path).
    Returns None when there is no photo, and the intro draws a silhouette instead."""
    path = os.path.join(base_dir, 'examples', file_name)
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as fh:
        return 'data:image/jpeg;base64,' + base64.b64encode(fh.read()).decode()


def build_frames(base_dir):
    return [{'label': label, 'img': photo(base_dir, f), 'colour': colour} for label, f, colour in FAMILY]


def intro_html(base_dir):
    """Reads hero_intro.html and fills in the three frames, the big family frame and the makers' names."""
    path = os.path.join(base_dir, 'hero_intro.html')
    if not os.path.exists(path):
        return '<div>hero_intro.html not found</div>'
    with open(path, encoding='utf-8') as fh:
        template = fh.read()
    names = ''.join(f'<b>{n}</b>' for n in MAKERS)                 # one name per line, all the same style
    return (template.replace('__FRAMES__', json.dumps(build_frames(base_dir)))
                    .replace('__FAMILY_PHOTO__', json.dumps(photo(base_dir, 'family.jpg')))
                    .replace('__MAKERS__', names))
