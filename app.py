import os
import base64
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS  # للسماح بتلقي الطلبات من المتجر المفتوح في المتصفح

app = Flask(__name__)
CORS(app)  # تفعيل CORS لحل مشاكل الحظر بين النطاقات

# جلب التوكن بأمان من بيئة تشغيل السيرفر
GITHUB_TOKEN = os.environ.get("SUPER_SECRET_GITHUB_TOKEN")
GITHUB_USER = "Yoyoreg"
REPO_NAME = "market-assets"
BRANCH = "main"

def get_github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

# 1. مسار رفع الصور والملفات
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        data = request.json
        if not data or 'content' not in data or 'product_name' not in data:
            return jsonify({"status": "error", "message": "بيانات غير مكتملة"}), 400
        
        # تجهيز اسم ملف فريد بناءً على الوقت الحالي
        import time
        file_name = f"img_{int(time.time() * 1000)}.png"
        
        # رابط الـ API الخاص بـ GitHub لإنشاء ملف
        url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/products/{file_name}"
        
        # إرسال الطلب إلى GitHub
        payload = {
            "message": f"نشر صورة منتج: {data['product_name']}",
            "content": data['content'],  # النص الـ Base64 الممرر من المتصفح
            "branch": BRANCH
        }
        
        response = requests.put(url, headers=get_github_headers(), json=payload)
        
        if response.status_code == 201:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{BRANCH}/products/{file_name}"
            return jsonify({"status": "success", "url": raw_url}), 200
        else:
            return jsonify({"status": "error", "message": f"فشل الرفع لجيتهاب: {response.status_code}", "details": response.text}), response.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 2. مسار حذف الصور باستخدام الرابط (URL)
@app.route('/delete', methods=['POST'])
def delete_file():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"status": "error", "message": "الرابط مطلوب للحذف"}), 400
        
        target_url = data['url']
        
        # استخراج اسم الملف من الرابط المرسل
        # مثال للرابط: https://raw.githubusercontent.com/Yoyoreg/market-assets/main/products/img_12345.png
        if "products/" not in target_url:
            return jsonify({"status": "error", "message": "رابط الملف غير صالح أو لا يتبع للمجلد الصحيح"}), 400
            
        file_name = target_url.split("products/")[-1]
        
        # لحذف ملف من جيتهاب نحتاج أولاً لجلب الـ SHA الخاص به
        api_url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/products/{file_name}?ref={BRANCH}"
        get_res = requests.get(api_url, headers=get_github_headers())
        
        if get_res.status_code != 200:
            return jsonify({"status": "error", "message": "الملف غير موجود في المستودع أو تم حذفه مسبقاً"}), 404
            
        file_sha = get_res.json().get('sha')
        
        # إرسال طلب الحذف الفعلي
        delete_payload = {
            "message": f"حذف صورة منتج: {file_name}",
            "sha": file_sha,
            "branch": BRANCH
        }
        
        delete_res = requests.delete(f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/products/{file_name}", headers=get_github_headers(), json=delete_payload)
        
        if delete_res.status_code == 200:
            return jsonify({"status": "success", "message": "ok"}), 200
        else:
            return jsonify({"status": "error", "message": "فشل إتمام عملية الحذف سحابياً"}), delete_res.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # تشغيل محلي للتجربة، عند الرفع لـ Render سيتم تشغيله عبر gunicorn تلقائياً
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
