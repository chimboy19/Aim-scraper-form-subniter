import asyncio
import csv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

async def crawl_single_url(crawler, url, config):
    try:
        print(f"Starting crawl for: {url}")
        results = await crawler.arun(url, config=config)
        print(f"Completed crawl for: {url} - Found {len(results)} pages")
        return results
    except Exception as e:
        print(f"Error crawling {url}: {str(e)}")
        return []

async def main():
    # List of URLs to crawl
    urls_to_crawl = [
       "",
       "",
       ""
    ]

    # Configure the crawler
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,  # Reduced depth for multiple URLs
            max_pages=20,  # Reduced pages per URL
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.6),
            options={"ignore_links": True}
        ),
        verbose=False  # Less verbose output for multiple URLs
    )

    all_results = []
    
    async with AsyncWebCrawler() as crawler:
        # Create tasks for all URLs
        tasks = [crawl_single_url(crawler, url, config) for url in urls_to_crawl]
        
        # Run crawls concurrently with limited concurrency
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        for url_results in results:
            if isinstance(url_results, Exception):
                print(f"Error in crawl task: {url_results}")
            elif url_results:
                all_results.extend(url_results)

    print(f"\nTotal pages crawled: {len(all_results)}")

    # Save all results to CSV
    with open("multi_url_results.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["URL", "Source URL", "Markdown Content", "Depth"])
        
        for result in all_results:
            url = result.url
            source_url = result.metadata.get("source_url", "direct")
            depth = result.metadata.get("depth", 0)
            
            markdown_content = ""
            if result.markdown:
                if hasattr(result.markdown, "fit_markdown"):
                    markdown_content = result.markdown.fit_markdown or ""
                elif isinstance(result.markdown, str):
                    markdown_content = result.markdown
            
            # Truncate very long content for CSV
            markdown_content = markdown_content[:5000] + ("..." if len(markdown_content) > 5000 else "")
            
            writer.writerow([url, source_url, markdown_content, depth])

    print("All results saved to 'multi_url_results.csv'")

if __name__ == "__main__":
    asyncio.run(main())