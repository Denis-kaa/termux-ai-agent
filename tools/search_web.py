"""
Поиск в DuckDuckGo HTML. Парсинг результатов, ротация User-Agent, retry с backoff.
"""
from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from contracts.constants import HTTP_TIMEOUT_S, HTTP_RETRY_ATTEMPTS, HTTP_RETRY_BACKOFF_S, USER_AGENTS
from contracts.enums import ErrorCode
from infra.logger import get_logger
from tools.factories import create_success_result, create_error_result

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    raise ImportError(
        f"Missing dependencies for search_web: {e}. Install with: pip install -r requirements.txt"
    ) from e

CAPTCHA_MARKERS: tuple[str, ...] = ("captcha", "robot check", "are you a human", "unusual traffic")


class SearchWebTool:
    """Реализует BaseTool Protocol."""
    
    @property
    def tool_name(self) -> str:
        return "search_web"
    
    def execute(self, params: Mapping[str, Any], correlation_id: str) -> 'ToolResult':
        logger = get_logger('tools.search_web', correlation_id)
        start_time = time.time()
        
        query = params.get('query', '')
        if not query:
            return create_error_result(self.tool_name, correlation_id, 0, ErrorCode.PARSE_FAILED.value, "Empty query")
        
        last_error = None
        for attempt in range(HTTP_RETRY_ATTEMPTS + 1):
            ua = USER_AGENTS[attempt % len(USER_AGENTS)]
            try:
                response = requests.get(
                    'https://html.duckduckgo.com/html/',
                    params={'q': query},
                    headers={'User-Agent': ua},
                    timeout=HTTP_TIMEOUT_S,
                )
                
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    if attempt < HTTP_RETRY_ATTEMPTS:
                        time.sleep(HTTP_RETRY_BACKOFF_S[attempt])
                    continue
                
                if _is_captcha(response.text):
                    last_error = "captcha_detected"
                    if attempt < HTTP_RETRY_ATTEMPTS:
                        time.sleep(HTTP_RETRY_BACKOFF_S[attempt])
                    continue
                
                results = _parse_results(response.text)
                duration_ms = int((time.time() - start_time) * 1000)
                
                return create_success_result(
                    tool=self.tool_name,
                    correlation_id=correlation_id,
                    duration_ms=duration_ms,
                    data={"query": query, "results": results[:5]},
                )
            except requests.RequestException as e:
                last_error = str(e)
                if attempt < HTTP_RETRY_ATTEMPTS:
                    time.sleep(HTTP_RETRY_BACKOFF_S[attempt])
        
        duration_ms = int((time.time() - start_time) * 1000)
        return create_error_result(
            tool=self.tool_name,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            error_code=ErrorCode.HTTP_ERROR.value,
            error_details=f"All {HTTP_RETRY_ATTEMPTS + 1} attempts failed. Last: {last_error}",
        )


def _is_captcha(html: str) -> bool:
    html_lower = html.lower()
    return any(marker in html_lower for marker in CAPTCHA_MARKERS)


def _parse_results(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for result in soup.find_all('div', class_='result'):
        title_elem = result.find('a', class_='result__title') or result.find('a', class_='result__url')
        snippet_elem = result.find('a', class_='result__snippet')
        if not title_elem and not snippet_elem:
            continue
        title = title_elem.get_text(strip=True) if title_elem else ""
        url = title_elem.get('href', '') if title_elem else ""
        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
        if title or snippet:
            results.append({'title': title, 'snippet': snippet, 'url': url})
    return results
