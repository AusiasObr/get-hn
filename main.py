import requests
import trafilatura
import json
import os
import re
from dataclasses import dataclass
from typing import Literal

@dataclass
class Story:
    url: str
    title: str
    content: str
    score: int
    type: Literal["article", "youtube"]

TOP_STORIES_COUNT = 10
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
OUTPUT_DIR = "hn_stories"
MASTER_FILE = "daily_podcast_source.md"
YOUTUBE_URLS_FILE = "youtube_links.txt"

def is_youtube_url(url):
    """Checks if the URL is a YouTube link."""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return re.match(youtube_regex, url) is not None

def get_best_stories():
    """Fetches the top story IDs from HN."""
    response = requests.get(f"{HN_API_BASE}/beststories.json")
    response.raise_for_status()
    return response.json()

def get_item_details(item_id):
    """Fetches details for a specific HN item."""
    response = requests.get(f"{HN_API_BASE}/item/{item_id}.json")
    response.raise_for_status()
    return response.json()

def scrape(url) -> str | None:
    """Downloads article content using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None

        content = trafilatura.extract(downloaded, output_format='markdown')
        if not content:
            return None

        return content
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def main():
    print(f"--- HN Daily Summary: {TOP_STORIES_COUNT} Stories ---\n")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    story_ids = get_best_stories()
    processed_count = 0
    collected_stories = []

    for item_id in story_ids:
        if processed_count >= TOP_STORIES_COUNT:
            break

        item = get_item_details(item_id)
        url = item.get("url")
        if not url or "news.ycombinator.com" in url:
            continue

        title = item.get("title")
        score = item.get("score")

        print(f"[{processed_count + 1}] Processing: {title}")

        story_type = "youtube" if is_youtube_url(url) else "article"
        content = ""

        if story_type == "article":
            content = scrape(url)
            if not content:
                print(f"   Skipping: Could not extract content.")
                continue

        story_obj = Story(url=url, title=title, content=content, score=score, type=story_type)
        collected_stories.append(story_obj)
        processed_count += 1

    if collected_stories:
        master_path = os.path.join(OUTPUT_DIR, MASTER_FILE)
        with open(master_path, "w", encoding="utf-8") as f:
            f.write("# Hacker News Daily Briefing\n\n")
            f.write("This document contains the top stories from Hacker News for today's podcast discussion.\n\n")
            for i, s in enumerate(collected_stories):
                f.write(f"## Story {i+1}: {s.title}\n")
                f.write(f"Source URL: {s.url}\n")
                f.write(f"HN Score: {s.score} points\n\n")
                if s.type == "youtube":
                    f.write("> [Action] Please analyze the YouTube link above for this segment.\n\n")
                else:
                    f.write(f"{s.content}\n\n")
                f.write("---\n\n")

        yt_links = [s.url for s in collected_stories if s.type == "youtube"]
        if yt_links:
            yt_file_path = os.path.join(OUTPUT_DIR, YOUTUBE_URLS_FILE)
            with open(yt_file_path, "w", encoding="utf-8") as f:
                f.write(", ".join(yt_links))
            print(f"YouTube links saved to: {yt_file_path}")

        print(f"\nMaster Podcast Source created at: {master_path}")

    print(f"Done! Processed {processed_count} stories.")

if __name__ == "__main__":
    main()