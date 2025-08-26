import re
import json
from collections import Counter
from typing import List, Dict, Any, Optional, TypedDict, cast
from textblob import TextBlob
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# --- تعريف أنواع البيانات لتحسين قراءة الكود وتقليل الأخطاء ---
class Post(TypedDict):
    platform: str
    title: str
    views: int
    likes: int
    url: str

class SentimentInfo(TypedDict):
    post: Post
    sentiment: float

class AnalysisResults(TypedDict):
    most_viewed: Post
    most_liked: Post
    most_loved: SentimentInfo
    most_hated: SentimentInfo
    top_keywords: List[tuple[str, int]]

def fetch_twitter_mock_data() -> List[Post]:
    """
    هذه الدالة تقوم بمحاكاة جلب البيانات من تويتر ومنصات أخرى (باستثناء يوتيوب الذي يتم كشطه).
    في تطبيق حقيقي، ستقوم هنا باستدعاء واجهات برمجية (APIs) حقيقية.
    """
    mock_posts: List[Post] = [
        {'platform': 'Twitter', 'title': 'إطلاق هاتف جديد بميزات ثورية يثير الجدل', 'views': 500000, 'likes': 25000, 'url': 'https://twitter.com/status/xyz1'},
        {'platform': 'TikTok', 'title': 'تحدي الطبخ الجديد ينتشر بسرعة', 'views': 8000000, 'likes': 950000, 'url': 'https://tiktok.com/v/def2'},
        {'platform': 'Facebook', 'title': 'نقاش حاد حول قانون العمل الجديد', 'views': 300000, 'likes': 8000, 'url': 'https://facebook.com/post/ghi3'},
        {'platform': 'Instagram', 'title': 'صور مذهلة من حفل توزيع الجوائز', 'views': 1200000, 'likes': 250000, 'url': 'https://instagram.com/p/jkl4'},
        {'platform': 'Twitter', 'title': 'فشل إطلاق صاروخ فضائي يسبب خيبة أمل كبيرة', 'views': 750000, 'likes': 12000, 'url': 'https://twitter.com/status/pqr6'},
    ]
    return mock_posts

def _parse_youtube_views(views_text: str) -> int:
    """
    دالة مساعدة لتحويل نص عدد المشاهدات في يوتيوب إلى رقم صحيح.
    مثال: "1.2 مليون مشاهدة" -> 1200000
    """
    # تنظيف النص من الكلمات والرموز غير الضرورية
    cleaned_text = views_text.replace('مشاهدة', '').replace(',', '').strip()
    
    views = 0
    if 'ألف' in cleaned_text:
        views = int(float(cleaned_text.replace('ألف', '').strip()) * 1000)
    elif 'مليون' in cleaned_text:
        views = int(float(cleaned_text.replace('مليون', '').strip()) * 1000000)
    elif cleaned_text.isdigit():
        views = int(cleaned_text)
    
    return views

def scrape_youtube_trending() -> List[Post]:
    """
    تقوم هذه الدالة بكشط صفحة تريند يوتيوب لجلب الفيديوهات الرائجة.
    تعتمد هذه الطريقة على بنية صفحة يوتيوب، وقد تتوقف عن العمل إذا غير يوتيوب تصميم موقعه.
    """
    print("جاري جلب تريند يوتيوب عن طريق Web Scraping...")
    url = "https://www.youtube.com/feed/trending"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # التأكد من نجاح الطلب
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # بيانات يوتيوب غالباً ما تكون ضمن متغير JavaScript يسمى ytInitialData
        scripts = soup.find_all('script')
        data_script = None
        # Use a more robust way to find the script tag content
        for script in scripts:
            if script.string and 'ytInitialData' in str(script.string):
                data_script = str(script.string)
                break
        
        if not data_script:
            print("لم يتم العثور على بيانات التريند في صفحة يوتيوب.")
            return [] # Return early if no data is found
            
        # استخلاص الجزء الخاص بـ JSON من السكربت
        json_data_str = data_script.split(' = ')[1]
        # إزالة الفاصلة المنقوطة في النهاية إذا وجدت
        if json_data_str.endswith(';'):
            json_data_str = json_data_str[:-1]
            
        data: Dict[str, Any] = json.loads(json_data_str)
        
        # المسار إلى الفيديوهات قد يتغير، هذا المسار صحيح حالياً. نستخدم try-except للتعامل مع التغييرات المحتملة.
        try:
            video_items = data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['shelfRenderer']['content']['expandedShelfContentsRenderer']['items']
        except (KeyError, IndexError) as e:
            print(f"فشل في تحليل بنية بيانات يوتيوب، ربما تغير تصميم الموقع. الخطأ: {e}")
            return []
        
        youtube_trends: List[Post] = []
        for item in video_items:
            if 'videoRenderer' not in item:
                continue
            video = item['videoRenderer']
            views_text = video.get('viewCountText', {}).get('simpleText', '0')

            youtube_trends.append({
                'platform': 'YouTube',
                'title': video['title']['runs'][0]['text'],
                'views': _parse_youtube_views(views_text),
                'likes': 0, # الإعجابات غير متوفرة مباشرة في صفحة التريند
                'url': 'https://youtube.com/watch?v=' + video['videoId']
            })
        return youtube_trends

    except Exception as e:
        print(f"حدث خطأ أثناء جلب بيانات يوتيوب: {e}")
        return []

def analyze_trends(posts: List[Post]) -> Optional[AnalysisResults]:
    """
    تقوم هذه الدالة بتحليل قائمة المنشورات المستلمة.
    """
    if not posts:
        print("لا توجد بيانات لتحليلها.")
        return None

    print("جاري تحليل البيانات المستلمة...")

    # 1. تحليل المشاعر للعثور على المحتوى الأكثر حباً وكراهية
    sentiments: List[SentimentInfo] = []
    for post in posts:
        # استخدام TextBlob لتحليل النص. القطبية (polarity) تتراوح من -1 (سلبي جداً) إلى +1 (إيجابي جداً)
        sentiment = TextBlob(post['title']).sentiment.polarity
        sentiments.append({'post': post, 'sentiment': sentiment})
    
    # 2. استخراج الكلمات المفتاحية الأكثر استخداماً
    all_titles = ' '.join(p['title'] for p in posts)
    # تنظيف النص من الرموز غير المرغوب فيها وتحويله إلى كلمات صغيرة
    words = re.findall(r'\b\w+\b', all_titles.lower())
    
    # قائمة بكلمات شائعة (stop words) لتجاهلها في التحليل
    # يمكنك إضافة المزيد من الكلمات العربية هنا
    stop_words = set(['من', 'عن', 'في', 'و', 'أو', 'إلى', 'هو', 'هي', 'هذا', 'هذه', 'جدا'])
    meaningful_words = [word for word in words if word not in stop_words and not word.isdigit()]
    
    # حساب تكرار الكلمات
    word_counts = Counter(meaningful_words)

    # 3. تجميع كل النتائج في قاموس واحد منظم
    analysis: AnalysisResults = {
        'most_viewed': sorted(posts, key=lambda p: p['views'], reverse=True)[0],
        'most_liked': sorted(posts, key=lambda p: p['likes'], reverse=True)[0],
        'most_loved': sorted(sentiments, key=lambda s: s['sentiment'], reverse=True)[0],
        'most_hated': sorted(sentiments, key=lambda s: s['sentiment'])[0],
        'top_keywords': word_counts.most_common(5)
    }

    return analysis

def display_results(analysis: Optional[AnalysisResults]) -> None:
    """
    تقوم هذه الدالة بعرض النتائج بطريقة منظمة وسهلة الفهم.
    """
    if not analysis:
        return

    print("\n" + "="*40)
    print("📊 تقرير التريندات على مواقع التواصل 📊")
    print("="*40 + "\n")

    # عرض النتائج الرئيسية
    mv = analysis['most_viewed']
    print(f"🔥 الأكثر مشاهدة:")
    print(f"   - العنوان: \"{mv['title']}\"")
    print(f"   - المنصة: {mv['platform']}")
    print(f"   - المشاهدات: {mv['views']:,}")
    print(f"   - الرابط: {mv['url']}\n")

    ml = analysis['most_liked']
    # التحقق من أن هناك منشورات لديها إعجابات
    if ml['likes'] > 0:
        print(f"❤️ الأكثر إعجاباً:")
        print(f"   - العنوان: \"{ml['title']}\"")
        print(f"   - المنصة: {ml['platform']}")
        print(f"   - الإعجابات: {ml['likes']:,}")
        print(f"   - الرابط: {ml['url']}\n")

    # عرض نتائج تحليل المشاعر
    loved = analysis['most_loved']
    print(f"😍 التريند الأكثر إيجابية (حباً):")
    print(f"   - العنوان: \"{loved['post']['title']}\"")
    print(f"   - المنصة: {loved['post']['platform']}")
    print(f"   - درجة الإيجابية: {loved['sentiment']:.2f}")
    print(f"   - الرابط: {loved['post']['url']}\n")

    hated = analysis['most_hated']
    print(f"😠 التريند الأكثر سلبية (كرهاً):")
    print(f"   - العنوان: \"{hated['post']['title']}\"")
    print(f"   - المنصة: {hated['post']['platform']}")
    print(f"   - درجة السلبية: {hated['sentiment']:.2f}")
    print(f"   - الرابط: {hated['post']['url']}\n")

    # عرض الكلمات المفتاحية
    keywords = analysis['top_keywords']
    if keywords:
        print("🔑 الكلمات المفتاحية الأكثر استخداماً:")
        for keyword, count in keywords:
            print(f"   - \"{keyword}\" (تكررت {count} مرات)")

    print("\n" + "="*40)
    print("انتهى التقرير.")
    print("="*40)

def fetch_all_trends() -> List[Post]:
    """
    دالة رئيسية لتجميع التريندات من كل المصادر المتاحة.
    تتجاوز المصادر التي تفشل وتكمل بالباقي.
    """
    all_posts: List[Post] = []
    print("="*40)
    print("بدء عملية جلب التريندات من جميع المصادر...")
    
    # المصدر الأول: يوتيوب (عبر كشط الويب)
    all_posts.extend(scrape_youtube_trending())
    
    # المصدر الثاني: تويتر (بيانات وهمية حالياً)
    # يمكنك استبدالها بدالة تستخدم API حقيقي
    all_posts.extend(fetch_twitter_mock_data())
    
    print(f"\nتم جلب ما مجموعه {len(all_posts)} منشوراً من جميع المصادر.")
    return all_posts

if __name__ == "__main__":
    # 1. جلب البيانات
    social_media_posts: List[Post] = fetch_all_trends()
    
    # 2. تحليل البيانات
    analyzed_data: Optional[AnalysisResults] = analyze_trends(social_media_posts)
    
    # 3. عرض النتائج
    display_results(analyzed_data)
