from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

TEMPLATE_QR_PATH = Path("static/resource/templates/template_qr.pdf")
RESOURCE_ROOT = Path("static/resource")

PDF_WIDTH = 595
PDF_HEIGHT = 842
QR_CONTAINER_X = 137
QR_CONTAINER_Y = 90
QR_CONTAINER_SIZE = 322
QR_INNER_PADDING = 16

QR_IMAGE_SIZE = 1400
QR_FOREGROUND = (15, 23, 42)
QR_BACKGROUND = (255, 255, 255)


def build_restaurant_qr_pdf(template_path, restaurant_url, restaurant_name, logo_resource_path=None):
    qr_image = build_restaurant_qr_image(
        restaurant_url=restaurant_url,
        restaurant_name=restaurant_name,
        logo_resource_path=logo_resource_path,
    )
    return merge_qr_with_template(template_path, qr_image)


def build_restaurant_qr_preview(restaurant_url, restaurant_name, logo_resource_path=None, output_size=900):
    qr_image = build_restaurant_qr_image(
        restaurant_url=restaurant_url,
        restaurant_name=restaurant_name,
        logo_resource_path=logo_resource_path,
    )
    preview = qr_image.resize((output_size, output_size), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    preview.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer


def build_restaurant_qr_image(restaurant_url, restaurant_name, logo_resource_path=None):
    qrcode = import_qrcode()
    StyledPilImage, RoundedModuleDrawer, SolidFillColorMask = import_qrcode_styles()

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=18,
        border=3,
    )
    qr.add_data(restaurant_url)
    qr.make(fit=True)

    qr_image = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(
            front_color=QR_FOREGROUND,
            back_color=QR_BACKGROUND,
        ),
    ).convert("RGBA")

    qr_image = qr_image.resize((QR_IMAGE_SIZE, QR_IMAGE_SIZE), Image.Resampling.LANCZOS)
    decorated = Image.new("RGBA", (QR_IMAGE_SIZE, QR_IMAGE_SIZE), (255, 255, 255, 0))
    decorated.paste(qr_image, (0, 0), qr_image)

    logo_badge = build_logo_badge(
        restaurant_name=restaurant_name,
        logo_resource_path=logo_resource_path,
        badge_size=int(QR_IMAGE_SIZE * 0.28),
    )
    badge_x = (QR_IMAGE_SIZE - logo_badge.width) // 2
    badge_y = (QR_IMAGE_SIZE - logo_badge.height) // 2
    decorated.alpha_composite(logo_badge, (badge_x, badge_y))
    return decorated


def build_logo_badge(restaurant_name, logo_resource_path=None, badge_size=390):
    badge = Image.new("RGBA", (badge_size, badge_size), (255, 255, 255, 0))
    shadow = Image.new("RGBA", (badge_size, badge_size), (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (22, 24, badge_size - 22, badge_size - 20),
        radius=int(badge_size * 0.28),
        fill=(15, 23, 42, 55),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
    badge.alpha_composite(shadow)

    draw = ImageDraw.Draw(badge)
    inset = 18
    draw.rounded_rectangle(
        (inset, inset, badge_size - inset, badge_size - inset),
        radius=int(badge_size * 0.26),
        fill=(255, 255, 255, 255),
        outline=(226, 232, 240, 255),
        width=max(3, badge_size // 70),
    )

    logo = load_restaurant_logo(logo_resource_path, int(badge_size * 0.58))
    if logo is not None:
        logo_x = (badge_size - logo.width) // 2
        logo_y = (badge_size - logo.height) // 2
        badge.alpha_composite(logo, (logo_x, logo_y))
        return badge

    render_badge_letter(badge, restaurant_name)
    return badge


def load_restaurant_logo(logo_resource_path, target_size):
    logo_path = resolve_resource_path(logo_resource_path)
    if not logo_path or not logo_path.exists():
        return None

    with Image.open(logo_path) as source_logo:
        logo = source_logo.convert("RGBA")

    logo.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
    logo_canvas = Image.new("RGBA", (target_size, target_size), (255, 255, 255, 0))
    paste_x = (target_size - logo.width) // 2
    paste_y = (target_size - logo.height) // 2
    logo_canvas.alpha_composite(logo, (paste_x, paste_y))
    return logo_canvas


def render_badge_letter(badge, restaurant_name):
    draw = ImageDraw.Draw(badge)
    text = (restaurant_name or "R").strip()[:1].upper() or "R"
    font_size = max(60, badge.width // 2)
    font = load_font(font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (badge.width - text_width) / 2 - bbox[0]
    y = (badge.height - text_height) / 2 - bbox[1] - badge.height * 0.02
    draw.text((x, y), text, font=font, fill=QR_FOREGROUND)


def merge_qr_with_template(template_path, qr_image):
    PdfReader, PdfWriter = import_pypdf()
    canvas = import_reportlab_canvas()

    template_file = Path(template_path)
    if not template_file.exists():
        raise FileNotFoundError(f"Template PDF not found: {template_file}")

    overlay_buffer = BytesIO()
    pdf_canvas = canvas.Canvas(overlay_buffer, pagesize=(PDF_WIDTH, PDF_HEIGHT))

    container_radius = 30
    pdf_canvas.saveState()
    pdf_canvas.setFillColorRGB(1, 1, 1)
    pdf_canvas.roundRect(QR_CONTAINER_X, QR_CONTAINER_Y, QR_CONTAINER_SIZE, QR_CONTAINER_SIZE, container_radius, stroke=0, fill=1)
    pdf_canvas.setStrokeColorRGB(226 / 255, 232 / 255, 240 / 255)
    pdf_canvas.setLineWidth(1)
    pdf_canvas.roundRect(QR_CONTAINER_X, QR_CONTAINER_Y, QR_CONTAINER_SIZE, QR_CONTAINER_SIZE, container_radius, stroke=1, fill=0)
    pdf_canvas.restoreState()

    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format="PNG", optimize=True)
    qr_buffer.seek(0)
    qr_reader = Image.open(qr_buffer)

    qr_draw_size = QR_CONTAINER_SIZE - (QR_INNER_PADDING * 2)
    pdf_canvas.drawInlineImage(
        qr_reader,
        QR_CONTAINER_X + QR_INNER_PADDING,
        QR_CONTAINER_Y + QR_INNER_PADDING,
        width=qr_draw_size,
        height=qr_draw_size,
    )
    pdf_canvas.showPage()
    pdf_canvas.save()
    overlay_buffer.seek(0)

    template_reader = PdfReader(str(template_file))
    overlay_reader = PdfReader(overlay_buffer)

    writer = PdfWriter()
    overlay_page = overlay_reader.pages[0]
    for index, page in enumerate(template_reader.pages):
        merged_page = page
        if index == 0:
            merged_page.merge_page(overlay_page)
        writer.add_page(merged_page)

    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer


def resolve_resource_path(resource_path):
    if not resource_path:
        return None

    normalized = Path(str(resource_path).replace("\\", "/"))
    candidate = (RESOURCE_ROOT / normalized).resolve()
    resource_root = RESOURCE_ROOT.resolve()

    if not str(candidate).startswith(str(resource_root)):
        return None
    return candidate


def load_font(font_size):
    for font_name in ("DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(font_name, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def import_qrcode():
    import qrcode

    return qrcode


def import_qrcode_styles():
    from qrcode.image.styles.colormasks import SolidFillColorMask
    from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
    from qrcode.image.styledpil import StyledPilImage

    return StyledPilImage, RoundedModuleDrawer, SolidFillColorMask


def import_pypdf():
    from pypdf import PdfReader, PdfWriter

    return PdfReader, PdfWriter


def import_reportlab_canvas():
    from reportlab.pdfgen import canvas

    return canvas
