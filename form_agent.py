import asyncio
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from browser_use import Agent
from langchain_openai import ChatOpenAI

# Company info (easy to update)
company_info = {
    "name": "Aim",
    "industry": "AIソリューション",
    "email": "marumo.m@aim-next.com",
    "phone": "07013860615",
    "furigana": "まるもみずき",
    "address": "〒162-0056 東京都新宿区若松町38-19",
    "website": "https://aim-next.com/ja-jp",
    "services": "AIソリューション、UI/UXデザイン、AIエージェント",
    "employees": "1-32名",
    "contact_person": "丸茂 瑞喜",
    "inquiry_type": "事業に関するお問い合わせ"
}

# --- URLs to process ---
urls_to_process = [
    # NTT Communications - Inquiry

    
    #"https://form.jotform.com/251483496258468",
    #"https://www.jotform.com/form/251403311718548",
    #"https://krs.bz/nextone/m/corporate_contact",
    "https://ywr.co.jp"
    # JETRO - Business Inquiry
    # Tokyo International Communication Committee
    # Kudan Japanese Language School
    # Add more URLs as needed
    
]

async def main():
    if not urls_to_process:
        print("No URLs provided. Please add URLs to the 'urls_to_process' list.")
        return

    # Prepare URLs as a newline-separated string for the prompt
    urls_block = "\n".join(urls_to_process)

    agent = Agent(
        task=f"""
✅ AI Agent Task Prompt: Website Outreach & AI Solution Suggestion. You are an AI agent that auto-fills contact forms and submits them.
Make sure it is able to fill all required details in the form.

🎯 Objective:
Visit each of the target URLs below, analyze the company's services, industry, and tone, and perform the following actions for each website:

🔗 Target URLs:
{urls_block}

Important Instructions:

1. Analyze the following:

    - Extract the company name from the website (look for <title> tags, headers, or company name in the contact page)
    - Identify the company's services and industry from the content.
    - Company's services, industry, and tone.

1. Contact Form Search:
    - Immediately search for a contact/inquiry form on the page.
    - Look for forms labeled "Contact", "Contact Us", "Inquiry", "お問い合わせ", or similar (in both English and Japanese).
    - If no contact/inquiry form is found, or if the form cannot be submitted, **report "No form found" and move to the next URL without delay.**

2. Special Requirements:
    - If the form requires katakana, furigana, or other specific formats, use the correct format for each field. For example, if a field requires katakana, use the katakana version of the name.
    - If you are unsure, use "マルモ ミズキ" for katakana and "まるも みずき" for hiragana.
    - Always fill all required fields. If a required field is not in the provided company info, use a realistic placeholder.

3. Generate a Japanese Marketing Message:
    - Extract the company name from the website (look for <title> tags, headers, or company name in the contact page). If not found, use "御社".
    - Generate a new, original, 200-word Japanese marketing message about Aim, using the extracted company name in the greeting.
    - **Do NOT copy any text from the target website.**
    - The message must:
        - Introduce Aim and show understanding of the target company's services/industry.
        - Highlight how Aim's AI/UX solutions can support their operations, tailored to their industry.
        - Emphasize synergies (e.g., improving workflows, enhancing customer experience, automating internal processes).
        - Start with: "Dear [Actual Extracted Company Name],"
        - End with: ご検討いただければ幸いです。敬具
        Generate a Japanese marketing message (200 words):

    Example:    

    Tone: Professional & collaborative.

    Format:

    [Start by extracting the company name from the website content]

    Dear [Actual Extracted Company Name],

    [Introduce Aim and show understanding of their services/industry.]

    [Highlight how Aim's AI/UX solutions can support their operations, tailored to their industry.]

    [Emphasize synergies: e.g., improving workflows, enhancing customer experience, or automating internal processes.]

    [Include a call to action with our website link: {company_info['website']}]

    ご検討いただければ幸いです。

    敬具

4. Auto-fill and Submit:
    - Use the following company details:
        会社名: {company_info['name']}
        業種: {company_info['industry']}
        メールアドレス: {company_info['email']}
        電話番号: {company_info['phone']}
        フリガナ: {company_info['furigana']}
        住所: {company_info['address']}
        ウェブサイト: {company_info['website']}
        サービス: {company_info['services']}
        従業員数: {company_info['employees']}
        担当者名: {company_info['contact_person']}
        お問い合わせ種別: {company_info['inquiry_type']}
        メッセージ: Use the full, original, 200-word Japanese marketing message you generated above.

    - The message must introduce Aim, mention our AI/UX solutions, reference the target company's industry, and include a call to action with our website link ({company_info['website']}). 
    - Use the extracted company name in the greeting.
    - Choose the relevant inquiry type (e.g., {company_info['inquiry_type']}).
    - Submit the form and verify submission by checking for a confirmation message.
    - If the form shows an error (such as incorrect input or validation failure), attempt to fix the error and resubmit only once.
    - If the form still cannot be submitted after one correction, report the error, mark as "Manual submission required", and move to the next URL without further retries.
    - Never attempt more than one correction per form. Never enter a retry loop.

5. Complex Form Handling:
    If the form is complex due to:
    - Multi-step process
    - Advanced validation
    - CAPTCHA requirements
    - Dynamic fields
    Then:
    a) Fill all possible fields  
    b) Save the form state  
    c) Generate clear human submission instructions  
    d) Mark this form as "Manual submission required"
        
6. Manual Submission Handling:
    - If the form is too complex to auto-submit (for example, due to advanced validation, dynamic fields, or other technical barriers), **report "Manual submission required" for that URL, and keep the browser tab open for manual review and submission.**
    - Clearly indicate in your summary which URLs require manual submission.

7. Error Handling:
    - If you encounter a CAPTCHA, login wall, or a form you cannot fill, skip and report the reason.
    - If any required field cannot be filled, report the field name and move to the next URL.
    - Never leave the company name as "[Company Name]" in the final message


After all URLs, provide a summary table with:
- URL
- Company name found (if any)
- Form found (yes/no)
- Submission successful (yes/no)
- Manual submission required (yes/no)
- Any error or confirmation message
- The exact message submitted in the メッセージ field
        """,
        llm=ChatOpenAI(model="gpt-4o"),
    )
    result = await agent.run()
    # Save agent output for review with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"agent_results_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write(str(result))
    print(f"\nAgent run complete. Results saved to agent_results_{timestamp}.txt")

    # Print manual submission URLs if possible
    try:
        import json
        agent_result = json.loads(result)
        print_manual_submission_urls(agent_result)
    except Exception:
        print("Could not parse agent result for manual submission URLs.")

def print_manual_submission_urls(agent_result):
    print("\n--- URLs Requiring Manual Submission ---")
    for entry in agent_result:
        if entry.get("Manual submission required", "").lower() == "yes":
            print(entry.get("URL", "Unknown URL"))

if __name__ == "__main__":
    asyncio.run(main())
