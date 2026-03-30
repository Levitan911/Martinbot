import logging
from typing import Optional
from firecrawl import Firecrawl
from conf.settings import config

logger = logging.getLogger(__name__)

FIRECRAWL_API_KEY = config.martin.skills.FIRECRAWL_API_KEY


class WebSearchTool:
    """
    基于 Firecrawl v2 的轻量级搜索工具。
    特点：搜索 + 自动抓取全文，输出 LLM 友好的 Markdown。
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = FIRECRAWL_API_KEY
        if not self.api_key:
            raise ValueError("缺少 FIRECRAWL_API_KEY 配置")
        
        self.client = Firecrawl(api_key=self.api_key)
        logger.info("WebSearchTool 已就绪 (Firecrawl v2)")

    def search_and_scrape(self, query: str, limit: int = 3, max_chars: int = 3000) -> str:
        """
        搜索并读取前 N 个结果的全文。
        
        Args:
            query: 搜索词
            limit: 结果数量 (建议 3-5)
            max_chars: 单篇文章最大字符数 (防 Token 溢出)
            
        Returns:
            格式化的 Markdown 字符串
        """
        logger.info(f"🔍 搜索: '{query}' (Limit: {limit})")
        
        try:
            # 1. 搜索
            # 返回对象包含 .web, .news, .images 属性
            search_res = self.client.search(query=query, limit=limit)
            
            if not search_res or not search_res.web:
                return "未找到相关搜索结果。"

            results = []
            # 2. 串行抓取
            for i, item in enumerate(search_res.web, 1):
                url = item.url
                title = item.title or "无标题"
                
                try:
                    # 3. 抓取全文
                    scrape_res = self.client.scrape(url=url, formats=["markdown"])
                    
                    content = scrape_res.markdown if hasattr(scrape_res, 'markdown') else ""
                    if not content:
                        continue
                    
                    # 4. 智能截断
                    if len(content) > max_chars:
                        content = content[:max_chars] + "\n> ...(内容已截断)"
                    
                    # 5. 组装片段
                    results.append(
                        f"### {i}. {title}\n"
                        f"🔗 [{url}]({url})\n\n"
                        f"{content}\n"
                        f"{'-'*40}\n"
                    )
                    logger.info(f"✅ 已抓取: {url}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 抓取失败 {url}: {e}")
                    results.append(f"### {i}. {title}\n⚠️ 无法读取内容: {e}\n{'-'*40}\n")
            
            if not results:
                return "搜索到了链接，但无法获取任何页面内容。"
            
            return f"## 🌐 搜索结果: {query}\n\n" + "\n".join(results)
        
        except Exception as e:
            logger.error(f"❌ 搜索服务异常: {e}")
            return f"搜索出错: {str(e)}"


if __name__ == "__main__":
    tool = WebSearchTool()
    print(tool.search_and_scrape("今日热点新闻", limit=3))
