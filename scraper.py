import re
import json
import os
from typing import List, Dict, Any

import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
# استيراد تعريف Post من ملف التحليل لتجنب التكرار
from analyzer import Post

# --- إعداد Gemini API ---
# Define the constant once from the environment.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)  # type: ignore [reportPrivateImportUsage]
    else:
        print("تحذير: لم يتم العثور على مفتاح GEMINI_API_KEY في ملف .env. سيتم تعطيل ميزة التلخيص.")
except Exception as e:
    print(f"حدث خطأ أثناء إعداد Gemini: {e}")

def _parse_youtube_views(views_text: str) -> int:
    """دالة مساعدة لتحويل نص عدد المشاهدات في يوتيوب إلى رقم صحيح."""
    if not views_text:
        return 0
    # إزالة "مشاهدة" أو "views" والفاصلة
    cleaned_text = views_text.lower().replace('مشاهدة', '').replace('views', '').replace(',', '').strip()
    
    # استخلاص الرقم فقط
    value_text = ''.join(filter(lambda x: x.isdigit() or x == '.', cleaned_text))
    if not value_text:
        return 0
        
    value = float(value_text)

    if 'k' in cleaned_text or 'ألف' in cleaned_text:
        return int(value * 1000)
    if 'm' in cleaned_text or 'مليون' in cleaned_text:
        return int(value * 1000000)
    
    return int(value)

def summarize_with_gemini(url: str) -> str:
    """
    يأخذ رابط مقال، يقرأ محتواه، ثم يستخدم Gemini لتلخيصه.
    """
    if not GEMINI_API_KEY or not url or url == "#":  # Check the global flag
        return "ميزة التلخيص معطلة."

    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # استخلاص الفقرات النصية من المقال
        paragraphs = soup.find_all('p')
        article_text = ' '.join([p.get_text() for p in paragraphs])

        if not article_text:
            return "لم يتم العثور على محتوى في الرابط."

        model = genai.GenerativeModel('gemini-pro')  # type: ignore [reportPrivateImportUsage]
        prompt = f"لخص المقال التالي في جملة واحدة موجزة باللغة العربية:\n\n{article_text[:3000]}" # نأخذ أول 3000 حرف لتجنب النصوص الطويلة جداً
        summary_response = model.generate_content(prompt)  # type: ignore [reportUnknownMemberType]
        return summary_response.text.strip()
    except Exception as e:
        print(f"فشل تلخيص الرابط {url}: {e}")
        return "فشل في تلخيص المحتوى."

def scrape_youtube_trending() -> List[Post]:
    """يجلب أحدث التريندات من يوتيوب مع معلومات إضافية."""
    print("جاري جلب تريند يوتيوب...")
    url = "https://www.youtube.com/feed/trending"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
    }
    
    youtube_trends: List[Post] = []
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        scripts = soup.find_all('script')
        data_script = None
        for script in scripts:
            script_text = script.get_text()
            if 'ytInitialData' in script_text:
                data_script = script_text
                break
        
        if not data_script: return []
            
        json_data_str = data_script.split(' = ')[1]
        if json_data_str.endswith(';'): json_data_str = json_data_str[:-1]
        data: Dict[str, Any] = json.loads(json_data_str)
        
        # --- مسار مرن للوصول إلى الفيديوهات ---
        video_items = []
        try:
            # Path 1 (Newer layout)
            video_items = data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['richGridRenderer']['contents']
        except (KeyError, IndexError, TypeError):
            print("فشل المسار الأول ليوتيوب، جاري تجربة المسار الثاني...")
            try:
                # Path 2 (Older layout)
                video_items = data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
            except (KeyError, IndexError, TypeError) as e:
                print(f"فشل المسار الثاني ليوتيوب أيضاً. لا يمكن جلب البيانات. الخطأ: {e}")
                return []
        
        for item in video_items:
            # Handle multiple possible data structures
            video_renderer = None
            if item.get('richItemRenderer'):
                video_renderer = item.get('richItemRenderer', {}).get('content', {}).get('videoRenderer')
            elif item.get('videoRenderer'):
                video_renderer = item.get('videoRenderer')

            if not video_renderer:
                continue

            # --- استخراج آمن للبيانات ---
            video_id = video_renderer.get('videoId', '')
            if not video_id: continue

            title = video_renderer.get('title', {}).get('runs', [{}])[0].get('text', 'N/A')
            views_text = video_renderer.get('viewCountText', {}).get('simpleText', '0')
            
            nav_endpoint = video_renderer.get('navigationEndpoint', {})
            web_command = nav_endpoint.get('commandMetadata', {}).get('webCommandMetadata', {})
            video_url_path = web_command.get('url', '')

            thumbnails = video_renderer.get('thumbnail', {}).get('thumbnails', [])
            thumbnail_url = (thumbnails[-1].get('url') if thumbnails else "")

            youtube_trends.append({
                'platform': 'YouTube',
                'title': title,
                'views': _parse_youtube_views(views_text),
                'likes': 0, # الإعجابات غير متوفرة في صفحة التريند
                'url': 'https://youtube.com' + video_url_path,
                'thumbnail': thumbnail_url,
                'channel': video_renderer.get('longBylineText', {}).get('runs', [{}])[0].get('text', 'N/A'),
                'published_time': video_renderer.get('publishedTimeText', {}).get('simpleText', 'N/A'),
                'summary': '' # لا يوجد تلخيص لفيديوهات يوتيوب حالياً
            })
        return youtube_trends
    except requests.exceptions.RequestException as e:
        print(f"حدث خطأ في الشبكة أثناء جلب بيانات يوتيوب: {e}")
        return []
    except Exception as e:
        print(f"حدث خطأ غير متوقع أثناء جلب بيانات يوتيوب: {e}")
        return []

def scrape_google_trends() -> List[Post]:
    """يجلب أحدث المواضيع الرائجة من مؤشرات جوجل (للسعودية كمثال)."""
    print("جاري جلب تريندات مؤشرات جوجل...")
    # يمكنك تغيير geo=SA إلى بلد آخر مثل EG لمصر أو AE للإمارات
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=SA"
    google_trends: List[Post] = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        for item in root.findall('.//item')[:5]: # نأخذ أول 5 تريندات فقط لتجنب استهلاك API بشكل كبير
            # --- معالجة آمنة للبيانات لتجنب الأخطاء ---
            # جلب عدد المشاهدات مع قيمة افتراضية
            traffic_el = item.find('{https://trends.google.com/trends/approx_traffic}approx_traffic')
            views_text = traffic_el.text if traffic_el is not None and traffic_el.text else '0'
            views = int(re.sub(r'[\+,]', '', views_text or '0'))

            # جلب باقي البيانات مع قيم افتراضية
            title_el = item.find('title')
            title = (title_el.text or "بدون عنوان") if title_el is not None else "بدون عنوان"

            link_el = item.find('link')
            url = (link_el.text or "#") if link_el is not None else "#"

            # --- استدعاء Gemini للتلخيص ---
            # Only summarize if we have a valid URL
            summary = summarize_with_gemini(url) if url and url != "#" else "لا يوجد رابط صالح للتلخيص."

            thumbnail_el = item.find('{http://www.google.com/images/thumbnail}thumbnail')
            thumbnail = (thumbnail_el.get('url') or "") if thumbnail_el is not None else ""

            pub_date_el = item.find('pubDate')
            published_time = (pub_date_el.text or "") if pub_date_el is not None else ""

            google_trends.append({
                'platform': 'Google Trends',
                'title': title,
                'views': views,
                'likes': 0,
                'url': url,
                'thumbnail': thumbnail,
                'channel': 'Google Search',
                'published_time': published_time,
                'summary': summary,
            })
        return google_trends
    except requests.exceptions.RequestException as e:
        print(f"حدث خطأ في الشبكة أثناء جلب بيانات مؤشرات جوجل: {e}")
        return []
    except Exception as e:
        print(f"حدث خطأ غير متوقع أثناء جلب بيانات مؤشرات جوجل: {e}")
        return []

def fetch_all_trends() -> List[Post]:
    """دالة رئيسية لتجميع التريندات من كل المصادر المتاحة."""
    all_posts: List[Post] = []
    print("="*40)
    print("بدء عملية جلب التريندات من جميع المصادر...")
    
    all_posts.extend(scrape_youtube_trending())
    all_posts.extend(scrape_google_trends())
    
    print(f"\nتم جلب ما مجموعه {len(all_posts)} منشوراً من جميع المصادر.")
    return all_posts
