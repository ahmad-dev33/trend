from typing import List, Optional, TypedDict
from collections import Counter
import re
from textblob import TextBlob

# --- تعريف أنواع البيانات لتحسين قراءة الكود وتقليل الأخطاء ---
class Post(TypedDict):
    platform: str
    title: str
    views: int
    likes: int
    url: str
    thumbnail: str
    channel: str
    published_time: str
    summary: str

class SentimentInfo(TypedDict):
    post: Post
    sentiment: float

class AnalysisResults(TypedDict):
    most_viewed: Post
    most_liked: Post
    most_loved: SentimentInfo
    most_hated: SentimentInfo
    top_keywords: List[tuple[str, int]]

def analyze_trends(posts: List[Post]) -> Optional[AnalysisResults]:
    """تقوم هذه الدالة بتحليل قائمة المنشورات المستلمة."""
    if not posts:
        print("لا توجد بيانات لتحليلها.")
        return None

    print("جاري تحليل البيانات المستلمة...")

    sentiments: List[SentimentInfo] = []
    for post in posts:
        sentiment = TextBlob(post['title']).sentiment.polarity
        sentiments.append({'post': post, 'sentiment': sentiment})
    
    if not sentiments:
        print("فشل تحليل المشاعر، لا يمكن المتابعة.")
        return None

    all_titles = ' '.join(p['title'] for p in posts)
    words = re.findall(r'\b\w+\b', all_titles.lower())
    
    stop_words = set(['من', 'عن', 'في', 'و', 'أو', 'إلى', 'هو', 'هي', 'هذا', 'هذه', 'جدا', 'تم', 'علي', 'مع', 'بعد', 'أن'])
    meaningful_words = [word for word in words if word not in stop_words and not word.isdigit()]
    word_counts = Counter(meaningful_words)

    analysis: AnalysisResults = {
        'most_viewed': sorted(posts, key=lambda p: p['views'], reverse=True)[0],
        'most_liked': sorted(posts, key=lambda p: p['likes'], reverse=True)[0],
        'most_loved': sorted(sentiments, key=lambda s: s['sentiment'], reverse=True)[0],
        'most_hated': sorted(sentiments, key=lambda s: s['sentiment'])[0],
        'top_keywords': word_counts.most_common(5)
    }
    return analysis
