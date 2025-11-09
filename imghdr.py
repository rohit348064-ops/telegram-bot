import imghdr

filename = "photo.jpg"
image_type = imghdr.what(filename)

print(image_type)