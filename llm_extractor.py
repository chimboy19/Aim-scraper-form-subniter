# paste the 


from groq import Groq
import csv
import os
from dotenv import load_dotenv
import textwrap
import openai
load_dotenv()

# Set your Groq API Key
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --- Chunking Function ---
def chunk_text(text, max_chars=3000):
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

# --- Step 1: Use ChatCompletion to extract structured info ---
def extract_company_info(content):
    response = client.chat.completions.create(
        # model="llama3-70b-8192",
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are an AI that extracts structured business information from unstructured text."
            },
            {
                "role": "user",
                "content": f"""
Extract the following details from the text below:

- Company Name
- Email
- Phone Number
- What they do (short summary)

Format the output as:
### Company Name: <company_name>
**Email:** <email>
**Phone Number:** <phone>
**About:** <description>

Only return the markdown content without any extra explanation.

Text:
{content}
                """
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content

# --- Step 2: Parse markdown into dictionary ---
def parse_llm_markdown(markdown_text):
    data = {
        "Company Name": "Not listed",
        "Email": "Not listed",
        "Phone Number": "Not listed",
        "About": "Not listed"
    }

    lines = markdown_text.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("### Company Name:"):
            data["Company Name"] = line.replace("### Company Name:", "").strip()
        elif line.startswith("**Email:**"):
            data["Email"] = line.replace("**Email:**", "").strip()
        elif line.startswith("**Phone Number:**"):
            data["Phone Number"] = line.replace("**Phone Number:**", "").strip()
        elif line.startswith("**About:**"):
            data["About"] = line.replace("**About:**", "").strip()

    return data

# --- Step 3: Save to CSV ---
def save_to_csv(data, filename="company_data.csv"):
    fieldnames = ["Company Name", "Email", "Phone Number", "About"]
    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)
        print(f"✅ Saved: {data['Company Name']}")

# --- Step 4: Main execution with chunking ---
def main():
    content = """
    


    """

    chunks = chunk_text(content, max_chars=3000)
    print(f"🔍 Total Chunks: {len(chunks)}")

    for i, chunk in enumerate(chunks, 1):
        print(f"🧩 Processing chunk {i}/{len(chunks)}")
        try:
            extracted_markdown = extract_company_info(chunk)
            parsed_data = parse_llm_markdown(extracted_markdown)
            save_to_csv(parsed_data)
        except Exception as e:
            print(f"⚠️ Error in chunk {i}: {e}")

if __name__ == "__main__":
    main()
