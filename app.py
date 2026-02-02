import os
from functools import wraps
from flask import Flask, render_template, abort, request, redirect, url_for, session, jsonify
from data import get_restaurants, get_restaurant, update_restaurant, update_menu_item
from qr import generate_qr
import analytics
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")
# Default theme assigned to new restaurants on signup. Can be set via environment variable.
RESTAURANT_DEFAULT_THEME = os.environ.get("RESTAURANT_DEFAULT_THEME", "default")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login", next=request.path))
        return f(*args, **kwargs)

    return decorated


@app.route("/")
def home():
    restaurants = get_restaurants()
    links = "".join([f"<li><a href='/{slug}'>{r['name']}</a></li>" for slug, r in restaurants.items()])
    return f"<h2>QR Menu SaaS</h2><ul>{links}</ul>"


@app.route("/<slug>")
def menu(slug):
    restaurant = get_restaurant(slug)
    if not restaurant:
        abort(404)

    # Record a page scan for analytics
    analytics.record_scan(slug)

    qr_path = generate_qr(slug)

    return render_template(
        "menu.html",
        restaurant=restaurant,
        qr_image=qr_path
    )


@app.route('/api/<slug>/item/<int:index>/click', methods=['POST'])
def api_click(slug, index):
    # record a click event; item index is recorded for ranking
    analytics.record_click(slug, index)
    return jsonify({'ok': True})


@app.route('/api/<slug>/click', methods=['POST'])
def api_click_generic(slug):
    # generic click without item (e.g., top-level order button)
    analytics.record_click(slug, None)
    return jsonify({'ok': True})


@app.route("/admin/<slug>/analytics")
@admin_required
def admin_analytics(slug):
    restaurant = get_restaurant(slug)
    if not restaurant:
        abort(404)
    now = datetime.utcnow()
    report = analytics.get_monthly_summary(slug, now.year, now.month)
    # add item names to top_items
    for it in report['top_items']:
        idx = it['index']
        if idx is None:
            it['name'] = 'General'
        else:
            try:
                it['name'] = restaurant['menu'][idx]['name']
            except Exception:
                it['name'] = f'Item {idx}'
    return render_template('admin_analytics.html', restaurant=restaurant, report=report, slug=slug)



def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login", next=request.path))
        return f(*args, **kwargs)

    return decorated


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    next_url = request.args.get("next") or url_for("home")
    if request.method == "POST":
        pw = request.form.get("password")
        if pw == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(next_url)
        return render_template("admin_login.html", error="Invalid password")
    return render_template("admin_login.html", error=None)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin/<slug>")
@admin_required
def admin_panel(slug):
    restaurant = get_restaurant(slug)
    if not restaurant:
        abort(404)
    return render_template("admin.html", restaurant=restaurant, slug=slug)


@app.route('/signup', methods=['POST'])
def signup():
    """Public signup endpoint to create a new restaurant. Expects JSON {
        "slug": "my-restaurant",
        "name": "My Restaurant",
        "whatsapp": "92300...",
        optional: "menu": []
    }
    New restaurant will get the server default theme when not specified.
    """
    data = request.get_json() or {}
    slug = data.get('slug')
    if not slug:
        return jsonify({'error': 'slug required'}), 400
    from data import create_restaurant, load_data
    # check exists
    if load_data().get(slug):
        return jsonify({'error': 'slug already exists'}), 400
    theme = data.get('theme') or RESTAURANT_DEFAULT_THEME
    restaurant = {
        'name': data.get('name', slug),
        'name_ur': data.get('name_ur', ''),
        'whatsapp': data.get('whatsapp', ''),
        'menu': data.get('menu', []),
        'theme': theme
    }
    success = create_restaurant(slug, restaurant, default_theme=RESTAURANT_DEFAULT_THEME)
    if not success:
        return jsonify({'error': 'creation failed'}), 500
    return jsonify({'ok': True, 'slug': slug, 'theme': theme}), 201


@app.route('/api/<slug>/theme', methods=['POST'])
@admin_required
def api_set_theme(slug):
    """Set per-restaurant theme (admin-only). Expects JSON {"theme": "traditional"|"default"}."""
    data = request.get_json() or {}
    theme = data.get('theme')
    if theme not in (None, 'default', 'traditional'):
        return jsonify({'error': 'invalid theme'}), 400
    # treat None or 'default' as clearing theme
    from data import set_restaurant_theme
    success = set_restaurant_theme(slug, theme if theme != 'default' else 'default')
    if not success:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'ok': True})


@app.route("/api/<slug>/menu")
def api_get_menu(slug):
    restaurant = get_restaurant(slug)
    if not restaurant:
        return jsonify({"error": "not found"}), 404
    return jsonify(restaurant)


@app.route("/api/<slug>/item/<int:index>/update", methods=["POST"])
@admin_required
def api_update_item(slug, index):
    data = request.get_json() or {}
    allowed = {"price", "is_available", "is_chefs_special", "name", "name_ur", "image_url", "category"}
    fields = {k: v for k, v in data.items() if k in allowed}
    # Convert is_available to bool if provided as string
    if "is_available" in fields:
        val = fields["is_available"]
        if isinstance(val, str):
            fields["is_available"] = val.lower() in ("1", "true", "yes")
    success = update_menu_item(slug, index, fields)
    if not success:
        return jsonify({"error": "update failed"}), 400
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)

