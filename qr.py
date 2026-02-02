import qrcode
import os

# Fix the space in the string
BASE_URL = "https://mitochondrial-cheyenne-dentirostral.ngrok-free.dev"

def generate_qr(slug):
    os.makedirs("static/qr", exist_ok=True)

    url = f"{BASE_URL}/{slug}"
    img = qrcode.make(url)

    path = f"static/qr/{slug}.png"
    img.save(path)

    return path
