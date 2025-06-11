import asyncio
import csv
import os
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import openai

# Load environment variables
load_dotenv()

class CombinedCrawlerExtractor:
    def __init__(self):
        self.llm_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def crawl_single_url(self, crawler, url, config):
        try:
            print(f"Starting crawl for: {url}")
            results = await crawler.arun(url, config=config)
            print(f"Completed crawl for: {url} - Found {len(results)} pages")
            return results
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return []

    async def crawl_websites(self, urls, output_csv="crawled_data.csv"):
        """Crawl multiple websites and save results to CSV"""
        config = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=2,
                max_pages=200,
                include_external=False
            ),
            scraping_strategy=LXMLWebScrapingStrategy(),
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(threshold=0.6),
                options={"ignore_links": True}
            ),
            verbose=False
        )

        all_results = []
        
        async with AsyncWebCrawler() as crawler:
            tasks = [self.crawl_single_url(crawler, url, config) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url_results in results:
                if isinstance(url_results, Exception):
                    print(f"Error in crawl task: {url_results}")
                elif url_results:
                    all_results.extend(url_results)

        print(f"\nTotal pages crawled: {len(all_results)}")

        # Save raw crawl results
        with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
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
                
                writer.writerow([url, source_url, markdown_content, depth])

        print(f"Raw crawl data saved to '{output_csv}'")
        return output_csv

    def chunk_text(self, text, max_chars=3000):
        """Split text into manageable chunks for LLM processing"""
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

    def extract_information(self, content, extraction_prompt):
        """
        Use LLM to extract information based on custom prompt
        Returns markdown formatted results
        """
        response = self.llm_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI that extracts structured information from unstructured text."
                },
                {
                    "role": "user",
                    "content": extraction_prompt + f"\n\nText to analyze:\n{content}"
                }
            ],
            temperature=0.2
        )

        return response.choices[0].message.content

    def parse_markdown_to_dict(self, markdown_text):
        """
        Parse markdown output from LLM into a dictionary
        Format should be:
        ### Key: Value
        or
        **Key:** Value
        """
        data = {}
        lines = markdown_text.splitlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith("### "):
                # Handle ### Key: Value format
                parts = line[4:].split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    data[key] = value
            elif line.startswith("**") and ":**" in line:
                # Handle **Key:** Value format
                key_part, value_part = line.split(":**", 1)
                key = key_part[2:].strip()
                value = value_part.strip()
                data[key] = value
        
        return data

    def process_crawled_data(self, input_csv, output_csv, extraction_prompt):
        """
        Process crawled data with LLM to extract specific information
        """
        # Read crawled data
        with open(input_csv, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            crawled_data = list(reader)

        # Prepare output CSV
        fieldnames = set()
        all_extracted_data = []

        print(f"\nProcessing {len(crawled_data)} crawled pages...")
        
        for i, row in enumerate(crawled_data, 1):
            print(f"Processing page {i}/{len(crawled_data)}: {row['URL']}")
            
            content = row["Markdown Content"]
            if not content:
                continue

            # Process in chunks if needed
            chunks = self.chunk_text(content)
            page_data = {"URL": row["URL"], "Source URL": row["Source URL"]}
            
            for chunk in chunks:
                try:
                    extracted_markdown = self.extract_information(chunk, extraction_prompt)
                    chunk_data = self.parse_markdown_to_dict(extracted_markdown)
                    
                    # Merge data from all chunks
                    for key, value in chunk_data.items():
                        if key not in page_data or page_data[key] == "Not listed":
                            page_data[key] = value
                            
                    # Collect all possible fieldnames
                    fieldnames.update(page_data.keys())
                except Exception as e:
                    print(f"Error processing chunk: {e}")
                    continue
            
            all_extracted_data.append(page_data)
            print(f"Extracted {len(page_data)-2} items from page {i}")

        # Ensure URL and Source URL are first columns
        final_fieldnames = ["URL", "Source URL"] + \
                         [f for f in fieldnames if f not in {"URL", "Source URL"}]
        
        # Write to output CSV
        with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=final_fieldnames)
            writer.writeheader()
            writer.writerows(all_extracted_data)

        print(f"\nExtracted data saved to '{output_csv}'")
        return output_csv

async def main():
    # Initialize the tool
    tool = CombinedCrawlerExtractor()

    # Websites to crawl
    urls_to_crawl = [
       "",
       ""
       
    ]

    # Step 1: Crawl websites
    crawled_csv = await tool.crawl_websites(urls_to_crawl)

    # Step 2: Define what to extract
    extraction_prompt = """
Extract the following details from the text:
focus on the remote jobs

- Company Name
- website
-location  remote or onsite 
- job posted
- What they do (short summary)
- Services offered
- Key products
- Year founded (if mentioned)

Format each finding as:
### Key: Value
or
**Key:** Value
"""

    # Step 3: Process crawled data with LLM
    extracted_csv = "extracted_data.csv"
    tool.process_crawled_data(crawled_csv, extracted_csv, extraction_prompt)

    print("\nProcessing complete!")
    print(f"- Raw crawl data: {crawled_csv}")
    print(f"- Extracted data: {extracted_csv}")

if __name__ == "__main__":
    asyncio.run(main())