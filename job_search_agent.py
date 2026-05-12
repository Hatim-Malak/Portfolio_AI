from langgraph.graph import StateGraph,START,END
from typing_extensions import TypedDict,Annotated
from pydantic import BaseModel,Field
from langchain_core.prompts import ChatPromptTemplate
import operator
from langchain_groq import ChatGroq
from typing import Literal
from dotenv import load_dotenv
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import By
import os
from tavily import TavilyClient
from jinja2 import Environment, FileSystemLoader
from fpdf import FPDF
from fpdf.enums import XPos, YPos
load_dotenv()



llm = ChatGroq(model="llama-3.1-8b-instant",temperature=0.5)
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

class ATSResumeBuilder(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_section_title(self, title):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(50, 54, 67) # Deep Charcoal #323643
        self.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.line(self.get_x(), self.get_y(), self.w - self.get_x(), self.get_y())
        self.ln(3)

class AgentState(TypedDict):
    job_url:str
    job_description:str
    required_fields:list[str]
    user_profile:dict
    generated_resume_path:str
    form_answer:Annotated[dict,operator.add]
    missing_info:list[str]
    status:str
    
class JobListing(BaseModel):
    title: str = Field(description="The title of the job, e.g., 'Software Engineer'")
    company: str = Field(description="The company hiring")
    compensation: str = Field(description="Salary range or compensation details")
    location: str = Field(description="Where the job is located or if it is Remote")
    description: str = Field(description="A concise summary of the job requirements, responsibilities, and tech stack.")
    
class JobBoard(BaseModel):
    job_1: JobListing = Field(description="The very first valid job posting found")
    job_2: JobListing = Field(description="The second valid job posting found")
    job_3: JobListing = Field(description="The third valid job posting found")
    
structured_extractor = llm.with_structured_output(JobBoard)
    
async def scrape_wellfound_jobs(url:str):
    
    options = ChromiumOptions()
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.headless = False
    
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(
            url
        )
        await asyncio.sleep(5)
        body_element = await tab._find_element(By.TAG_NAME, "body")
        
        clean_text = await body_element.text
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are a specialized Recruitment Data Extractor.\n\n"
                "### TASK\n"
                "Extract EXACTLY 3 valid job listings to fill the job_1, job_2, and job_3 slots. "
                "For each job, provide a concise 'description' that captures the tech stack and primary responsibilities.\n\n"
                "### DATA QUALITY\n"
                "- Focus on job titles: Software Engineer, MERN, AI Intern, etc.\n"
                "- Ignore generic company marketing blurbs.\n"
            )),
            ("human", "Find exactly 3 jobs and their summaries in this text:\n\n{text}")
        ])
        
        # Slicing to 3000 to keep the context dense and fast
        formatted_message = prompt.format_messages(text = clean_text[:3000])
        
        try:
            print(" Extracting exactly 3 jobs...")
            extracted_data = structured_extractor.invoke(formatted_message)
            
            print("\nEXTRACTION SUCCESSFUL:")
            for job in [extracted_data.job_1, extracted_data.job_2, extracted_data.job_3]:
                print(f"🏢 Company: {job.company}")
                print(f"💼 Title: {job.title}")
                print(f"💰 Pay: {job.compensation}")
                print(f"📍 Location: {job.location}")
                print(f"📝 Description: {job.description}...")
                print("-" * 30)
                
        except Exception as e:
            print(f"❌ Extraction Error: {e}")

def internship_search():
    search_query = (
        "Active Software Engineering Internship MERN stack AI backend "
        "remote OR Indore, M.P, India apply 2026"
    )
    
    response = tavily_client.search(
        query=search_query,
        search_depth="advanced", # 'advanced' does deep scraping for better snippets
        max_results=3,
        include_raw_content=False # We just want the URLs and summaries right now
    )
    found_jobs = []
    print("\n✅ TAVILY FOUND THESE LEADS:")
    for result in response['results']:
        print(f"🔗 URL: {result['url']}")
        print(f"📝 Snippet: {result['content'][:150]}...\n")
        
        found_jobs.append({
            "url": result['url'],
            "summary": result['content']
        })
    
    try:
        asyncio.run(scrape_wellfound_jobs(str(found_jobs[0]["url"])))
    except KeyboardInterrupt:
        print("\n🛑 Agent stopped by user.")

def generate_fpdf_resume(resume_data: dict, output_filename: str = "Hatim_Malak_ATS_Resume.pdf"):
    print("✍️ Ghostwriter is building your ATS PDF...")
    
    pdf = ATSResumeBuilder()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- HEADER ---
    pdf.set_font("helvetica", "B", 24)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, resume_data.get("name", "Hatim Malak"), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    contact_info = f"{resume_data.get('email', '')} | {resume_data.get('phone', '')} | {resume_data.get('linkedin', '')}"
    pdf.cell(0, 6, contact_info, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # --- TECHNICAL SKILLS ---
    pdf.add_section_title("TECHNICAL SKILLS")
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(0, 0, 0)
    skills = ", ".join(resume_data.get("skills", []))
    pdf.multi_cell(0, 6, f"Languages & Frameworks: {skills}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # --- PROJECTS ---
    pdf.add_section_title("PROJECTS & EXPERIENCE")
    for project in resume_data.get("projects", []):
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(130, 6, project.get("name", ""))
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 6, project.get("date", ""), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("helvetica", "I", 11)
        pdf.cell(0, 6, f"{project.get('role', '')} | {project.get('tech_stack', '')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("helvetica", "", 11)
        for bullet in project.get("bullets", []):
            # 1. Print the hyphen bullet without moving to a new line
            pdf.cell(5, 6, "- ") 
            
            # 2. FIXED: Calculate the exact remaining width for the multi_cell
            # Effective Width (pdf.epw) - current X offset
            current_x = pdf.get_x()
            safe_width = pdf.w - current_x - pdf.r_margin
            
            pdf.multi_cell(safe_width, 6, bullet, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)

    # --- EDUCATION ---
    pdf.add_section_title("EDUCATION")
    edu = resume_data.get("education", {})
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(130, 6, edu.get("university", "Chameli Devi Group of Institutions (CDGI), Indore"))
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, edu.get("grad_year", "Expected 2028"), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", "I", 11)
    pdf.cell(0, 6, edu.get("degree", "B.Tech Information Technology"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(output_filename)
    print(f"✅ Resume successfully saved to {output_filename}")
    return os.path.abspath(output_filename)

# Test the function
if __name__ == "__main__":
    test_data = {
        "name": "Hatim Malak",
        "email": "hatim@example.com",
        "phone": "+91 9876543210",
        "linkedin": "linkedin.com/in/hatimmalak",
        "skills": ["Python", "LangChain", "MERN Stack", "FastAPI"],
        "projects": [{
            "name": "Crumbs - Semantic Search",
            "date": "Jan 2026 - Present",
            "role": "Backend & AI Developer",
            "tech_stack": "Python, ChromaDB, HuggingFace",
            "bullets": [
                "Engineered a semantic search system bypassing traditional keyword matching.",
                "Integrated local LLMs to process unstructured data securely."
            ]
        }],
        "education": {
            "university": "CDGI, Indore",
            "degree": "B.Tech Information Technology",
            "grad_year": "Expected 2028"
        }
    }
    generate_fpdf_resume(test_data)