import qrcode

url = " https://mitochondrial-cheyenne-dentirostral.ngrok-free.dev"

img = qrcode.make(url)
img.save("menu2_qr.png")

print("QR Code created successfully!")
