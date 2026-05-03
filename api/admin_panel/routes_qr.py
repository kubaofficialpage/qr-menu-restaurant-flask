from flask import abort, redirect, render_template, send_file, url_for

from services.qr_pdf import TEMPLATE_QR_PATH, build_restaurant_qr_pdf, build_restaurant_qr_preview

from . import admin
from .auth import login_required
from .queries import require_restaurant


@admin.route("/qr")
@login_required
def qr_generator():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    restaurant_url = url_for("restaurant_home", restaurant_slug=restaurant["slug"], _external=True)
    return render_template(
        "admin/qr_generator.html",
        restaurant=restaurant,
        restaurant_url=restaurant_url,
        qr_template_path=str(TEMPLATE_QR_PATH).replace("\\", "/"),
    )


@admin.route("/qr/preview")
@login_required
def qr_preview():
    restaurant = require_restaurant()
    if not restaurant:
        abort(404)

    restaurant_url = url_for("restaurant_home", restaurant_slug=restaurant["slug"], _external=True)
    preview_buffer = build_restaurant_qr_preview(
        restaurant_url=restaurant_url,
        restaurant_name=restaurant["name"],
        logo_resource_path=restaurant.get("logo"),
    )
    return send_file(preview_buffer, mimetype="image/png")


@admin.route("/qr/download")
@login_required
def qr_download():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    restaurant_url = url_for("restaurant_home", restaurant_slug=restaurant["slug"], _external=True)
    pdf_buffer = build_restaurant_qr_pdf(
        template_path=TEMPLATE_QR_PATH,
        restaurant_url=restaurant_url,
        restaurant_name=restaurant["name"],
        logo_resource_path=restaurant.get("logo"),
    )
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{restaurant['slug']}-qr-a4.pdf",
    )
