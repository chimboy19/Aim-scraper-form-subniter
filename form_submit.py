

import asyncio
import json
import os
import random
import re
import time
from datetime import datetime
from dotenv import load_dotenv

import openai
import pandas as pd
from openai import AsyncOpenAI
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

# Initialize OpenAI async client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Enhanced company data with address components
company_data = {
    "company_name": "Aim",
    "industry": "AIソリューション",
    "email": "marumo.m@aim-next.com",
    "phone": "07013860615",
    "furigana": "丸茂 瑞喜",
    "address": {
        "postal": "〒162-0056",
        "prefecture": "東京都",
        "city": "新宿区",
        "street": "若松町38-19"
    },
    "website": "https://aim-next.com/ja-jp",
    "products": "AIソリューション、UI/UXデザイン、AIエージェント",
    "employees": "1-32名",
    "country": "日本",
    "contact_person": "丸茂 瑞喜",
    "message": """
弊社エイムは、カスタムAIソリューションを通じて業務効率化を実現するグローバルなAIエンジニアリングチームです。6カ国に展開する32名のエンジニアが、LLaMAなどの自社チューニング済みモデルを活用した迅速なオンプレミス開発を専門としております。

【主要業界別ソリューション】
■ 建設業界：
 - ARを用いた点検システム
 - テキストからBIM生成
 - 現場分析AI
■ 製造業界：
 - 図面検索エンジン
 - 生産計画エージェント
■ 不動産・人事：
 - 物件管理自動化
 - AI面接官システム
 - 深層プロファイリング
■ 金融・医療：
 - プライベート生成AI基盤
 - カスタムモデル導入支援

私たちは単なるソフトウェア開発ではなく、御社の強みを拡張するためのパートナーとしてチームに寄り添います。

AIを活用して御社のビジネスをどのように向上できるかについてご興味がございましたら、ぜひお気軽にご連絡ください。御社のビジネスへの適用可能性について、ぜひ議論させていただければ幸いです。
詳細については、弊社ウェブサイト（https://aim-next.com/ja-jp）もぜひご覧ください。""",
    "default_values": {
        "how_hear": "その他",
        "privacy_policy": True,
        "preferred_contact": "email"
    }
}

async def generate_japanese_value(field_name: str, field_type: str = None) -> str:
    """Generate realistic Japanese values for different field types"""
    last_names = ["佐藤", "鈴木", "高橋", "田中", "伊藤"]
    first_names = ["太郎", "健太", "直人", "美咲", "由紀"]
    
    if "name" in field_name.lower() or "氏名" in field_name:
        return f"{random.choice(last_names)} {random.choice(first_names)}"
    elif "email" in field_name.lower() or "メール" in field_name:
        return f"info{random.randint(100,999)}@example.com"
    elif "phone" in field_name.lower() or "電話" in field_name:
        return f"080-{random.randint(1000,9999)}-{random.randint(1000,9999)}"
    elif "postal" in field_name.lower() or "郵便" in field_name:
        return f"〒{random.randint(100,999)}-{random.randint(1000,9999)}"
    elif "prefecture" in field_name.lower() or "都道府県" in field_name:
        return random.choice(["東京都", "大阪府", "神奈川県"])
    elif "city" in field_name.lower() or "市区町村" in field_name:
        return random.choice(["新宿区", "渋谷区", "横浜市"])
    elif "address" in field_name.lower() or "住所" in field_name:
        return f"{random.choice(['東京都', '大阪府'])}{random.choice(['新宿区', '渋谷区'])}"
    elif "inquiry" in field_name.lower() or "問い合わせ" in field_name:
        return random.choice(["製品について", "サービスについて", "その他"])
    else:
        return f"自動入力{random.randint(1,100)}"

async def get_field_mapping_from_gpt(form_fields):
    system_prompt = """
You are an expert at mapping HTML form fields to company information. Analyze these form fields and:

1. Map to known company fields when possible (see list below)
2. Identify required fields
3. Suggest values for unmapped fields

Company fields available:
- company_name, contact_person, email, phone, address (postal, prefecture, city, street)
- message, industry, website, employees, country
- default_values (how_hear, privacy_policy, preferred_contact)

Return JSON with:
{
  "field_mappings": {
    "field_name": {
      "map_to": "company_field",
      "required": boolean,
      "generated_value": "value" (if not mapped)
    }
  }
}
"""
    user_prompt = f"Form fields to analyze: {json.dumps(form_fields, indent=2, ensure_ascii=False)}"
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Field mapping error: {e}")
        return {}

async def map_fields_with_intelligence(inputs, page, company_data):
    field_data = []
    for inp in inputs:
        try:
            field_data.append({
                "name": await inp.get_attribute("name"),
                "id": await inp.get_attribute("id"),
                "type": await inp.get_attribute("type"),
                "label": await inp.evaluate("el => el.labels?.[0]?.textContent || ''"),
                "placeholder": await inp.get_attribute("placeholder") or ""
            })
        except:
            continue

    ai_mapping = await get_field_mapping_from_gpt(field_data)
    if not ai_mapping:
        ai_mapping = {"field_mappings": {}}

    field_map = {}
    for inp in inputs:
        try:
            field_name = await inp.get_attribute("name") or await inp.get_attribute("id")
            if not field_name:
                continue

            mapping = ai_mapping["field_mappings"].get(field_name, {})
            mapped_to = mapping.get("map_to")
            
            if mapped_to and mapped_to in company_data:
                if mapped_to == "address" and isinstance(company_data["address"], dict):
                    if "postal" in field_name.lower():
                        value = company_data["address"]["postal"]
                    elif "prefecture" in field_name.lower():
                        value = company_data["address"]["prefecture"]
                    elif "city" in field_name.lower():
                        value = company_data["address"]["city"]
                    elif "street" in field_name.lower():
                        value = company_data["address"]["street"]
                    else:
                        value = f"{company_data['address']['prefecture']}{company_data['address']['city']}{company_data['address']['street']}"
                else:
                    value = company_data[mapped_to]
            else:
                if mapping.get("required", False):
                    value = mapping.get("generated_value") or await generate_japanese_value(field_name)
                else:
                    continue

            field_map[inp] = value
        except Exception as e:
            print(f"⚠️ Error processing field {field_name}: {e}")
            continue

    return field_map

async def check_submission_confirmation(page):
    """Check for submission confirmation messages or pages"""
    confirmation_indicators = [
        "送信完了", "送信ありがとうございました", "thank you", "success", 
        "確認メールを送信しました", "送信が完了しました", "confirmation",
        "ご連絡ありがとうございます", "受け付けました"
    ]
    
    try:
        content = await page.content()
        content_lower = content.lower()
        
        for indicator in confirmation_indicators:
            if indicator.lower() in content_lower:
                return True
        
        confirmation_selectors = [
            ".success-message", ".thank-you", ".confirmation",
            ".alert-success", ".message-success", "#success"
        ]
        
        for selector in confirmation_selectors:
            if await page.query_selector(selector):
                return True
                
        return False
    except Exception as e:
        print(f"⚠️ Error checking confirmation: {e}")
        return False

async def fill_and_submit_form(page, company_data):
    submission_method = None
    try:
        await page.wait_for_selector("form", timeout=10000)
        forms = await page.query_selector_all("form")
        if not forms:
            return {"status": "No form found", "submission_method": None}

        form = forms[-1]
        inputs = await form.query_selector_all("input, textarea, select")

        field_map = await map_fields_with_intelligence(inputs, page, company_data)
        auto_filled_fields = []

        for input_el, value in field_map.items():
            try:
                field_name = await input_el.get_attribute("name") or await input_el.get_attribute("id")
                auto_filled_fields.append(field_name)
                
                tag = await input_el.evaluate("el => el.tagName.toLowerCase()")
                input_type = await input_el.get_attribute("type") or "text"

                if tag == "select":
                    await input_el.select_option(value)
                elif input_type == "checkbox":
                    await input_el.set_checked(bool(value))
                elif input_type == "radio":
                    await input_el.evaluate(f"el => el.value === '{value}' && el.click()")
                else:
                    await input_el.fill(str(value))
            except Exception as e:
                print(f"⚠️ Failed to fill field: {e}")

        await handle_special_fields(page, company_data)

        if await check_for_missing_required_fields(page):
            print("⚠️ Required fields may be missing - entering manual mode")
            submission_method = "manual"
            await manual_form_completion(page)
        else:
            submission_method = "auto"
            submit_selector = "input[type='submit'], button[type='submit']"
            submit_buttons = await page.query_selector_all(submit_selector)
            
            if submit_buttons:
                await submit_buttons[0].click()
            else:
                await page.keyboard.press("Enter")

        try:
            await asyncio.sleep(2)
            if await check_submission_confirmation(page):
                return {
                    "status": "Submitted successfully",
                    "submission_method": submission_method,
                    "auto_filled_fields": auto_filled_fields
                }
            else:
                print("⚠️ No confirmation detected - entering manual verification")
                submission_method = "manual"
                return await manual_verification_mode(page, auto_filled_fields)
                
        except Exception as e:
            print(f"⚠️ Submission verification error: {e}")
            return {
                "status": "Submission verification failed",
                "submission_method": submission_method,
                "auto_filled_fields": auto_filled_fields
            }
            
    except PlaywrightTimeoutError:
        return {"status": "Form not found (timeout)", "submission_method": None}
    except Exception as e:
        return {"status": f"Error during submission: {e}", "submission_method": None}

async def manual_verification_mode(page, auto_filled_fields):
    """Allow user to manually verify submission"""
    print("\n" + "="*50)
    print("MANUAL VERIFICATION MODE")
    print("="*50)
    print("The script couldn't confirm the submission automatically.")
    print("Auto-filled fields:")
    for field in auto_filled_fields:
        print(f"  - {field}")
    print("\nOptions:")
    print("1. Form was submitted successfully (press 1 then Enter)")
    print("2. Form needs manual submission (press 2 then Enter)")
    print("="*50 + "\n")
    
    await page.bring_to_front()
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        return {
            "status": "Submitted successfully (manually verified)",
            "submission_method": "manual",
            "auto_filled_fields": auto_filled_fields
        }
    else:
        print("Please submit the form manually in the browser window...")
        input("Press Enter after manual submission...")
        
        if await check_submission_confirmation(page):
            return {
                "status": "Submitted successfully after manual intervention",
                "submission_method": "manual",
                "auto_filled_fields": auto_filled_fields
            }
        else:
            return {
                "status": "Manual submission may have failed",
                "submission_method": "manual",
                "auto_filled_fields": auto_filled_fields
            }

async def manual_form_completion(page):
    """Allow user to manually complete the form"""
    print("\n" + "="*50)
    print("MANUAL FORM COMPLETION MODE")
    print("="*50)
    print("Please complete any missing fields in the browser window")
    print("Press Enter when ready to submit...")
    print("="*50 + "\n")
    
    await page.bring_to_front()
    input("Press Enter after completing the form...")

async def check_for_missing_required_fields(page):
    """Check for validation errors"""
    try:
        error_selectors = [
            ".error", ".validation-error", ".required", "[aria-invalid='true']",
            "入力してください", "必須項目です", "この項目は必須です"
        ]
        
        for selector in error_selectors:
            errors = await page.query_selector_all(selector)
            if errors:
                print(f"⚠️ Found {len(errors)} validation errors")
                return True
        return False
    except Exception as e:
        print(f"⚠️ Error checking for validation errors: {e}")
        return False

async def handle_special_fields(page, company_data):
    """Handle common special fields"""
    try:
        privacy_selectors = [
            'input[name="privacy_policy"]',
            'input[name="agree_terms"]',
            'input[type="checkbox"]'
        ]
        for selector in privacy_selectors:
            checkbox = await page.query_selector(selector)
            if checkbox:
                await checkbox.set_checked(True)
                break

        hear_about_selectors = [
            'select[name="how_hear"]',
            'select[name="referral_source"]'
        ]
        for selector in hear_about_selectors:
            select = await page.query_selector(selector)
            if select:
                await select.select_option(company_data["default_values"]["how_hear"])
                break
    except Exception as e:
        print(f"⚠️ Special field handling error: {e}")

async def process_urls(urls, company_data):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        for url in urls:
            page = await context.new_page()
            try:
                print(f"\nProcessing: {url}")
                await page.goto(url, timeout=20000)
                await asyncio.sleep(random.uniform(1, 3))
                
                result = await fill_and_submit_form(page, company_data)
                screenshot_file = f"screenshots/submission_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                os.makedirs("screenshots", exist_ok=True)
                await page.screenshot(path=screenshot_file)
                
                results.append({
                    "url": url,
                    "status": result["status"],
                    "submission_method": result.get("submission_method"),
                    "auto_filled_fields": ", ".join(result.get("auto_filled_fields", [])),
                    "timestamp": datetime.now().isoformat(),
                    "screenshot": screenshot_file
                })
                
            except Exception as e:
                results.append({
                    "url": url,
                    "status": f"Error: {str(e)}",
                    "submission_method": None,
                    "auto_filled_fields": "",
                    "timestamp": datetime.now().isoformat(),
                    "screenshot": None
                })
                print(f"⚠️ Error processing {url}: {e}")
            finally:
                await page.close()

        await browser.close()
    return results

def save_to_excel(results):
    filename = f"results/submission_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    os.makedirs("results", exist_ok=True)
    df = pd.DataFrame(results)
    
    # Reorder columns for better readability
    df = df[[
        "url", "status", "submission_method", "auto_filled_fields",
        "timestamp", "screenshot"
    ]]
    
    df.to_excel(filename, index=False)
    print(f"✅ Results saved to {filename}")

async def main():
    urls_to_process = [
        "https://krs.bz/nextone/m/corporate_contact",
    ]
    
    start_time = time.time()
    results = await process_urls(urls_to_process, company_data)
    save_to_excel(results)
    print(f"\nCompleted in {time.time()-start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())