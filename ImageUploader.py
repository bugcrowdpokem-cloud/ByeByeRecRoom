import json, hmac, hashlib, base64, os, struct, io, cloudscraper
from PIL import Image

ACC_URL = "https://api.rec.net/api/images/v4/uploadsaved"
B_FILE = "token.json"

def get_sig(key_b64, uri, body):
    key = base64.b64decode(key_b64)
    h = hmac.new(key, digestmod=hashlib.sha256)
    h.update(uri.encode('ascii'))

    if body:
        h.update(struct.pack('<I', len(body)))
        if len(body) > 2048:
            step = len(body) // 16
            for i in range(16):
                h.update(body[i * step : i * step + 128])
        else:
            h.update(body)

    return base64.b64encode(h.digest()).decode()


def fail(msg):
    print(f"[ERROR] {msg}")
    raise SystemExit


def main():
    print("Upload")

    if not os.path.exists(B_FILE):
        fail(f"token.json not found in: {os.getcwd()}")

    try:
        with open(B_FILE) as f:
            auth = json.load(f)
    except Exception as e:
        fail(f"Failed to read token.json: {e}")

    if "access_token" not in auth or "key" not in auth:
        fail("token.json is missing required fields: access_token / key")

    path = input("Image Path: ").strip().strip('"')

    if not os.path.exists(path):
        fail(f"Image not found: {path}")

    try:
        img = Image.open(path).convert("RGBA")
    except Exception as e:
        fail(f"Failed to load image: {e}")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_data = buf.getvalue()

    uri = "/api/images/v4/uploadsaved"
    bd = "BestHTTP_HTTPMultiPartForm_8249FBB0"

    meta = json.dumps({
        "playerIds": None,
        "savedImageType": 1,
        "roomId": 1,
        "playerEventId": 0,
        "accessibility": 0,
        "description": None
    }, separators=(',', ':'))

    body = (
        f"--{bd}\r\n"
        f"Content-Disposition: form-data; name=\"imgMeta\"\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(meta)}\r\n\r\n"
        f"{meta}\r\n"
        f"--{bd}\r\n"
        f"Content-Disposition: form-data; name=\"image\"; filename=\"file.png\"\r\n"
        f"Content-Type: image/png\r\n"
        f"Content-Length: {len(img_data)}\r\n\r\n"
    ).encode() + img_data + f"\r\n--{bd}--\r\n".encode()

    headers = {
        "Authorization": f"Bearer {auth['access_token']}",
        "X-RNSIG": get_sig(auth['key'], uri, body),
        "Content-Type": f"multipart/form-data; boundary={bd}",
        "User-Agent": "BestHTTP"
    }

    scraper = cloudscraper.create_scraper()

    print("Uploading...")

    r = scraper.post(ACC_URL, data=body, headers=headers)

    print(f"HTTP Status: {r.status_code}")

    if r.status_code != 200:
        print("Response:")
        print(r.text)
        fail("Upload failed.")

    try:
        res = r.json()
    except:
        fail("Server returned non-JSON response.")

    if "ImageName" not in res:
        print(res)
        fail("Upload succeeded but ImageName missing.")

    print("\nUpload Complete")
    print(f"Image URL: https://img.rec.net/{res['ImageName']}")


if __name__ == "__main__":
    main()