"""News data collection and JSON export."""

import requests
from bs4 import BeautifulSoup
import time
import re
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from app.config import settings

# ============================================================================
# 1. 네이버 뉴스 API 수집
# ============================================================================


class NaverNewsCollector:
    """네이버 뉴스 검색 API를 사용한 뉴스 메타데이터 수집"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://openapi.naver.com/v1/search/news.json"

        # 뉴스 카테고리별 키워드 정의
        self.categories = {
            "복지": ["노인복지", "기초연금", "장기요양", "복지정책"],
        }

    def search_news(self, keyword: str, display: int = 100) -> List[Dict]:
        """네이버 뉴스 검색"""
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

        params = {
            "query": keyword,
            "display": display,  # 최대 100개
            "sort": "date",  # 최신순
        }

        try:
            response = requests.get(
                self.base_url, headers=headers, params=params, timeout=10
            )
            response.raise_for_status()

            items = response.json().get("items", [])
            print(f"  '{keyword}': {len(items)}개 검색")
            return items

        except Exception as e:
            print(f"  '{keyword}' 검색 실패: {e}")
            return []

    def clean_html(self, text: str) -> str:
        """HTML 태그 및 특수문자 제거"""
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&quot;", '"').replace("&apos;", "'")
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def parse_date(self, date_str: str) -> str:
        """날짜 파싱"""
        try:
            dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def process_item(self, item: Dict, keyword: str, category: str) -> Dict:
        """뉴스 아이템 전처리"""
        return {
            "category": category,
            "keyword": keyword,
            "title": self.clean_html(item.get("title", "")),
            "description": self.clean_html(item.get("description", "")),
            "link": item.get("originallink", item.get("link", "")),
            "pub_date": self.parse_date(item.get("pubDate", "")),
            "source": (
                item.get("link", "").split("/")[2]
                if "/" in item.get("link", "")
                else "unknown"
            ),
        }

    def collect_all(
        self, display_per_keyword: int = 50, delay: float = 0.1
    ) -> List[Dict]:
        """전체 카테고리 뉴스 수집"""
        all_news = []

        print("=" * 60)
        print("뉴스 메타데이터 수집 시작")
        print("=" * 60)

        for category, keywords in self.categories.items():
            print(f"\n[{category}] 카테고리 수집 중...")

            for keyword in keywords:
                # API 호출
                items = self.search_news(keyword, display=display_per_keyword)

                # 전처리
                for item in items:
                    processed = self.process_item(item, keyword, category)
                    # 너무 짧은 뉴스 제외
                    if len(processed["description"]) >= 50:
                        all_news.append(processed)

                # API 호출 제한 대비 딜레이
                time.sleep(delay)

            print(
                f"  → {category} 완료: {sum(1 for n in all_news if n['category'] == category)}개"
            )

        print("\n" + "=" * 60)
        print(f"총 {len(all_news)}개 뉴스 수집 완료")
        print("=" * 60)

        # 중복 제거 (같은 링크)
        seen_links = set()
        unique_news = []
        for news in all_news:
            if news["link"] not in seen_links:
                seen_links.add(news["link"])
                unique_news.append(news)

        print(f"중복 제거 후: {len(unique_news)}개")
        return unique_news


# ============================================================================
# 2. 기사 본문 크롤링
# ============================================================================
class NewsContentCrawler:
    """뉴스 기사 본문 크롤러"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def extract_content(self, url: str) -> Optional[str]:
        """URL에서 기사 본문 추출"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")

            # 다양한 뉴스 사이트에 대응하는 본문 추출
            content = self._extract_by_selectors(soup)

            if content and len(content) > 100:
                # 불필요한 공백 정리
                content = re.sub(r"\s+", " ", content).strip()
                return content

            return None

        except Exception as e:
            print(f"    크롤링 실패: {str(e)[:50]}")
            return None

    def _extract_by_selectors(self, soup: BeautifulSoup) -> Optional[str]:
        """다양한 CSS 셀렉터로 본문 추출 시도"""
        # 우선순위 순 셀렉터 목록
        selectors = [
            "#dic_area",  # 네이버 뉴스
            "#articeBody",
            ".article_view",
            "article",  # 일반 뉴스
            ".article-body",
            ".article_body",
            ".article-content",
            ".news-content",
            ".news_body",
            ".view-content",
            '[itemprop="articleBody"]',
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # 스크립트, 스타일 태그 제거
                for tag in element.find_all(["script", "style", "iframe", "ins"]):
                    tag.decompose()

                text = element.get_text(separator=" ", strip=True)

                if len(text) > 100:
                    return text

        # 셀렉터로 못 찾으면 p 태그 모으기
        paragraphs = soup.find_all("p")
        if paragraphs:
            text = " ".join([p.get_text(strip=True) for p in paragraphs])
            if len(text) > 100:
                return text

        return None

    def crawl_articles(
        self,
        news_items: List[Dict],
        delay: float = 0.5,
        max_articles: Optional[int] = None,
    ) -> List[Dict]:
        """뉴스 리스트의 본문 크롤링"""
        print("\n" + "=" * 60)
        print("기사 본문 크롤링 시작")
        print("=" * 60)

        total = (
            len(news_items)
            if max_articles is None
            else min(len(news_items), max_articles)
        )
        success_count = 0

        # max_articles가 지정된 경우 해당 개수만 처리
        items_to_process = news_items[:total] if max_articles else news_items

        for idx, news in enumerate(items_to_process):
            url = news["link"]

            if (idx + 1) % 10 == 0:  # 10개마다 진행상황 출력
                print(f"  진행: {idx + 1}/{total} ({success_count}개 성공)")

            # 본문 추출
            content = self.extract_content(url)

            if content:
                news["full_content"] = content
                success_count += 1
            else:
                news["full_content"] = news.get(
                    "description", ""
                )  # 실패 시 description 사용

            time.sleep(delay)

        print(f"\n크롤링 완료: 성공 {success_count}/{total}개")
        print("=" * 60)

        return items_to_process


# ============================================================================
# 3. 뉴스 데이터 수집 및 저장
# ============================================================================


def collect_news_data(max_articles: Optional[int] = None):
    """뉴스 데이터 수집 및 JSON 저장 (ChromaDB 벡터화는 news_data_ingest.py에서 수행)

    Args:
        max_articles: 크롤링할 최대 기사 수 (None이면 전체, 테스트는 10 권장)
    """

    # 1. 네이버 뉴스 API로 메타데이터 수집
    print("\n[Step 1/3] 네이버 뉴스 API 수집")
    collector = NaverNewsCollector(
        client_id=settings.naver_client_id,
        client_secret=settings.naver_client_secret,
    )
    raw_news = collector.collect_all(display_per_keyword=100)

    if not raw_news:
        print("⚠️ 수집된 뉴스가 없습니다.")
        return

    # 2. 기사 본문 크롤링
    print(f"\n[Step 2/3] 기사 본문 크롤링 (최대 {max_articles or '전체'}개)")
    crawler = NewsContentCrawler()
    news_with_content = crawler.crawl_articles(
        raw_news, delay=0.5, max_articles=max_articles
    )

    if not news_with_content:
        print("⚠️ 크롤링된 기사가 없습니다.")
        return

    # 3. JSON 파일로 저장 (work_data 패턴)
    print("\n[Step 3/3] JSON 파일 저장")

    raw_dir = settings.data_raw_dir
    os.makedirs(os.path.join(raw_dir, "news"), exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    merged_file = os.path.join(raw_dir, "news", "news_merged.json")
    timestamped_file = os.path.join(raw_dir, "news", f"news_{timestamp}.json")

    # JSON 저장 (타임스탬프 버전 - 백업용)
    with open(timestamped_file, "w", encoding="utf-8") as f:
        json.dump(news_with_content, f, ensure_ascii=False, indent=2)
    print(f"  백업: {timestamped_file}")

    # 병합 파일 (최신 버전 - ingest에서 사용)
    with open(merged_file, "w", encoding="utf-8") as f:
        json.dump(news_with_content, f, ensure_ascii=False, indent=2)
    print(f"  병합: {merged_file}")
    print(f"  총 {len(news_with_content)}개 기사 저장")

    print("\n" + "=" * 60)
    print(f"✓ 수집 완료: {len(news_with_content)}개 뉴스")
    print(f"✓ 저장 위치: {merged_file}")
    print(f"✓ 다음 단계: python -m agent.tools.news_data_ingest")
    print("=" * 60)


# ============================================================================
# 실행
# ============================================================================

if __name__ == "__main__":
    collect_news_data()
