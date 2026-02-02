import json
import os
from copy import deepcopy

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_restaurants():
    return load_data()


def get_restaurant(slug):
    return deepcopy(load_data().get(slug))


def update_restaurant(slug, new_restaurant):
    data = load_data()
    data[slug] = new_restaurant
    save_data(data)


def update_menu_item(slug, index, fields):
    data = load_data()
    rest = data.get(slug)
    if not rest:
        return False
    try:
        item = rest["menu"][index]
    except (IndexError, KeyError):
        return False
    item.update(fields)
    save_data(data)
    return True


def set_restaurant_theme(slug, theme):
    """Set a per-restaurant theme (e.g., 'traditional' or 'default'). Returns True on success."""
    data = load_data()
    rest = data.get(slug)
    if not rest:
        return False
    rest['theme'] = theme
    save_data(data)
    return True


def create_restaurant(slug, restaurant, default_theme='default'):
    """Create a new restaurant entry. Returns True on success, False if slug already exists."""
    data = load_data()
    if slug in data:
        return False
    # ensure minimal structure
    rest = {
        'name': restaurant.get('name', slug),
        'name_ur': restaurant.get('name_ur', ''),
        'whatsapp': restaurant.get('whatsapp', ''),
        'menu': restaurant.get('menu', []),
        'theme': restaurant.get('theme', default_theme)
    }
    data[slug] = rest
    save_data(data)
    return True

