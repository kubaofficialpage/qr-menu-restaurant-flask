import os
import re
import uuid

from flask import request
from PIL import Image

UPLOAD_FOLDER = "static/resource/img"
USER_PROFILE_UPLOAD_FOLDER = "static/resource/user_profiles"
OPERATOR_AVATAR_UPLOAD_FOLDER = "static/resource/operator_avatars"
BRANCH_QR_UPLOAD_FOLDER = "static/resource/branch_qr"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def compress_to_webp(input_path, output_path, quality=75, max_size=(800, 800)):
    img = Image.open(input_path)
    img = img.convert("RGBA" if img.mode in ("RGBA", "P") else "RGB")
    img.thumbnail(max_size)
    img.save(output_path, format="WEBP", quality=quality, method=6)


def get_restaurant_upload_folder(restaurant):
    folder = os.path.join(UPLOAD_FOLDER, restaurant["slug"])
    os.makedirs(folder, exist_ok=True)
    return folder


def get_user_profile_upload_folder():
    os.makedirs(USER_PROFILE_UPLOAD_FOLDER, exist_ok=True)
    return USER_PROFILE_UPLOAD_FOLDER


def get_operator_avatar_upload_folder():
    os.makedirs(OPERATOR_AVATAR_UPLOAD_FOLDER, exist_ok=True)
    return OPERATOR_AVATAR_UPLOAD_FOLDER


def get_branch_qr_upload_folder():
    os.makedirs(BRANCH_QR_UPLOAD_FOLDER, exist_ok=True)
    return BRANCH_QR_UPLOAD_FOLDER


def save_uploaded_image(image, upload_folder, relative_prefix, quality=75, max_size=(800, 800)):
    filename = f"{uuid.uuid4().hex}.webp"
    temp_path = os.path.join(upload_folder, "temp_" + filename)
    final_path = os.path.join(upload_folder, filename)

    image.save(temp_path)
    compress_to_webp(temp_path, final_path, quality=quality, max_size=max_size)
    os.remove(temp_path)

    return f"{relative_prefix}/{filename}"


def save_menu_image(image, restaurant):
    upload_folder = get_restaurant_upload_folder(restaurant)
    return save_uploaded_image(image, upload_folder, f"img/{restaurant['slug']}")


def save_restaurant_logo(image, restaurant):
    return save_menu_image(image, restaurant)


def save_user_avatar(image):
    upload_folder = get_user_profile_upload_folder()
    return save_uploaded_image(image, upload_folder, "user_profiles", quality=80, max_size=(600, 600))


def save_operator_avatar(image):
    upload_folder = get_operator_avatar_upload_folder()
    return save_uploaded_image(image, upload_folder, "operator_avatars", quality=80, max_size=(600, 600))


def save_branch_qr_image(image):
    upload_folder = get_branch_qr_upload_folder()
    return save_uploaded_image(image, upload_folder, "branch_qr", quality=90, max_size=(1200, 1200))


def delete_resource_file(resource_path):
    if not resource_path:
        return

    relative_path = resource_path.replace("\\", "/")
    if not (
        relative_path.startswith("img/")
        or relative_path.startswith("user_profiles/")
        or relative_path.startswith("operator_avatars/")
        or relative_path.startswith("branch_qr/")
    ):
        return

    file_path = os.path.normpath(os.path.join("static/resource", relative_path))
    resource_root = os.path.abspath("static/resource")
    absolute_path = os.path.abspath(file_path)

    if not absolute_path.startswith(resource_root):
        return

    if os.path.exists(absolute_path):
        os.remove(absolute_path)


def delete_menu_image(image_path):
    delete_resource_file(image_path)


def model_to_dict(model):
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


def day_key(value):
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def selected_restaurant_ids():
    restaurant_ids = []
    for restaurant_id in request.form.getlist("restaurant_ids"):
        if restaurant_id.isdigit():
            restaurant_ids.append(int(restaurant_id))
    return restaurant_ids


def form_checkbox_value(name):
    return 1 if request.form.get(name) == "on" else 0


def safe_int(value, default=0, minimum=None, maximum=None):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def restaurant_form_data():
    return {
        "name": request.form.get("name", "").strip(),
        "slug": request.form.get("slug", "").strip().lower(),
        "description": request.form.get("description", "").strip() or None,
        "classic_info": request.form.get("classic_info", "").strip() or None,
        "phone": request.form.get("phone", "").strip() or None,
        "email": request.form.get("email", "").strip().lower() or None,
        "address": request.form.get("address", "").strip() or None,
        "work_hours": request.form.get("work_hours", "").strip() or None,
        "admin_contact": request.form.get("admin_contact", "").strip() or None,
        "director_contact": request.form.get("director_contact", "").strip() or None,
        "opening_date": request.form.get("opening_date", "").strip() or None,
        "support_phone": request.form.get("support_phone", "").strip() or None,
        "support_email": request.form.get("support_email", "").strip().lower() or None,
        "map_2gis_url": request.form.get("map_2gis_url", "").strip() or None,
        "map_2gis_embed_url": request.form.get("map_2gis_embed_url", "").strip() or None,
    }


def slugify_restaurant_name(name):
    translit = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
        "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        "А": "a", "Б": "b", "В": "v", "Г": "g", "Д": "d", "Е": "e", "Ё": "e",
        "Ж": "zh", "З": "z", "И": "i", "Й": "y", "К": "k", "Л": "l", "М": "m",
        "Н": "n", "О": "o", "П": "p", "Р": "r", "С": "s", "Т": "t", "У": "u",
        "Ф": "f", "Х": "h", "Ц": "ts", "Ч": "ch", "Ш": "sh", "Щ": "sch", "Ъ": "",
        "Ы": "y", "Ь": "", "Э": "e", "Ю": "yu", "Я": "ya",
    })

    slug = (name or "").translate(translit)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug.lower()).strip("-")
    return slug or "restaurant"

