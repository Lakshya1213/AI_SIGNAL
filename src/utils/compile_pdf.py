import os
import sys

# Add project root to sys.path to allow running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from fpdf import FPDF
except ImportError:
    print("Installing fpdf2 automatically...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"])
    from fpdf import FPDF

from src.utils.logger import Logger

class MarkdownPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_margins(15, 20, 15)
        self.add_page()
        
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, "GraphOne Data Intelligence Pipeline - Architecture Design", align="R")
            self.ln(10)
            
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def build_pdf(md_path: str, pdf_path: str):
    if not os.path.exists(md_path):
        Logger.error(f"Markdown file not found: {md_path}")
        return
        
    Logger.info(f"Compiling {md_path} to PDF...")
    
    pdf = MarkdownPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(10, 30, 80) # Sleek deep blue
    pdf.cell(0, 15, "GraphOne Data Intelligence Pipeline", ln=True, align="L")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Architectural Design and Scaling Strategy", ln=True, align="L")
    pdf.ln(5)
    
    # Horizontal line
    pdf.set_draw_color(10, 30, 80)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(8)
    
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    in_code_block = False
    code_lines = []
    
    for line in lines:
        line_str = line.strip()
        
        # Handle code block / mermaid
        if line_str.startswith("```"):
            if in_code_block:
                # End of code block
                in_code_block = False
                pdf.set_font("Courier", "", 8.5)
                pdf.set_fill_color(240, 242, 245)
                pdf.set_text_color(50, 50, 50)
                
                # Render code block box
                code_text = "".join(code_lines).strip()
                pdf.multi_cell(0, 4, code_text, border=1, fill=True)
                pdf.ln(4)
                code_lines = []
            else:
                in_code_block = True
            continue
            
        if in_code_block:
            code_lines.append(line)
            continue
            
        # Parse Headings
        if line_str.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(10, 30, 80)
            pdf.ln(6)
            pdf.cell(0, 10, line_str[2:], ln=True)
            pdf.ln(3)
        elif line_str.startswith("## "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(20, 50, 120)
            pdf.ln(4)
            pdf.cell(0, 8, line_str[3:], ln=True)
            pdf.ln(2)
        elif line_str.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(50, 50, 50)
            pdf.ln(3)
            pdf.cell(0, 6, line_str[4:], ln=True)
            pdf.ln(1.5)
        # Parse Lists
        elif line_str.startswith("* ") or line_str.startswith("- "):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 40)
            # bullet point
            pdf.set_x(20)
            pdf.cell(5, 5, chr(149), ln=False)
            
            # Remove MD formatting like **bold**
            clean_text = line_str[2:]
            clean_text = clean_text.replace("**", "")
            # replace other markdown markers
            pdf.multi_cell(0, 5, clean_text)
        elif line_str.startswith("1. ") or line_str.startswith("2. ") or line_str.startswith("3. ") or line_str.startswith("4. "):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.set_x(20)
            # Find numbering
            idx = line_str.find(". ")
            number = line_str[:idx+1]
            pdf.cell(8, 5, number, ln=False)
            
            clean_text = line_str[idx+2:]
            clean_text = clean_text.replace("**", "")
            pdf.multi_cell(0, 5, clean_text)
        # Parse Table lines (simple render)
        elif line_str.startswith("|") and not ("---" in line_str):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(40, 40, 40)
            cols = [c.strip().replace("**", "") for c in line_str.split("|")[1:-1]]
            if cols:
                # Render columns side by side
                col_width = 180 / len(cols)
                for col in cols:
                    pdf.cell(col_width, 6, col, border=1)
                pdf.ln(6)
        # Standard Paragraph
        elif line_str:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 40)
            # Clean formatting
            clean_text = line_str.replace("**", "")
            pdf.multi_cell(0, 5, clean_text)
            pdf.ln(2)
            
    try:
        pdf.output(pdf_path)
        Logger.success(f"PDF successfully compiled and written to {pdf_path}")
    except Exception as e:
        Logger.error(f"Failed to write PDF: {e}")

if __name__ == "__main__":
    build_pdf("architecture.md", "architecture.pdf")
