from flask import Flask, render_template
from scraper import fetch_all_trends
from analyzer import analyze_trends

app = Flask(__name__)

@app.route('/')
def home():
    """
    الصفحة الرئيسية التي تجلب البيانات، تحللها، ثم تعرضها.
    """
    # 1. جلب البيانات
    all_posts = fetch_all_trends()
    
    # 2. تحليل البيانات
    analysis_results = analyze_trends(all_posts)
    
    # 3. عرض النتائج في الواجهة
    return render_template('index.html', analysis=analysis_results, posts=all_posts)

if __name__ == "__main__":
    print("="*50)
    print("تم تشغيل تطبيق التريندات!")
    print("افتح الرابط التالي في متصفحك: http://127.0.0.1:5000")
    print("="*50)
    app.run(debug=True)
