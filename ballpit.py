import base64
import io
from PIL import Image, ImageDraw


def tile() -> str:
    """
    Generates a seamlessly repeating base64-encoded JPEG image of a colorful ball pit pattern.
    Used by app.py as a dynamic CSS background tile.
    """
    size = 420
    img = Image.new("RGB", (size, size), "#0a3a52")
    draw = ImageDraw.Draw(img)

    # Colorful ball palette matching the "Best of Luck Nikki" theme
    balls = [
        # (x, y, radius, fill_color, highlight_color)
        (70, 70, 48, "#e7343c", "#ff6b72"),
        (200, 60, 52, "#ffc83d", "#ffdf85"),
        (340, 80, 44, "#20c3a6", "#61ebd3"),
        (130, 170, 50, "#2c84e0", "#6cb0f8"),
        (270, 175, 46, "#9246b0", "#bf75db"),
        (50, 270, 52, "#ff8a24", "#ffb26e"),
        (190, 280, 48, "#20c3a6", "#61ebd3"),
        (330, 270, 54, "#e7343c", "#ff6b72"),
        (110, 370, 46, "#ffc83d", "#ffdf85"),
        (250, 375, 50, "#2c84e0", "#6cb0f8"),
        (370, 370, 44, "#ff8a24", "#ffb26e"),
    ]

    for x, y, r, fill, highlight in balls:
        # Draw main sphere body
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)

        # Draw glossy specular highlight on top-left of each ball
        hr = int(r * 0.35)
        hx, hy = x - int(r * 0.35), y - int(r * 0.35)
        draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=highlight)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"