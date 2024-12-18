from PIL import Image
import os

for i in range(1000):
    img = Image.open(f"TestData/image-{i}.gif")
    img.convert("RGBA")
    img.save(f"TestData/image-{i}.png")
    img.close()
    os.remove(f"TestData/image-{i}.gif")