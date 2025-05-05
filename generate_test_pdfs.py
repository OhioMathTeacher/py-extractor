import os
from reportlab.pdfgen import canvas

# Change this to wherever you want your test PDFs
test_dir = os.path.expanduser("~/test_metadata_pdfs")
os.makedirs(test_dir, exist_ok=True)

# 1. Embedded metadata
p = os.path.join(test_dir, "embedded_meta.pdf")
c = canvas.Canvas(p)
c.setTitle("Embedded Metadata PDF")
c.setAuthor("Jane Doe")
c.drawString(100, 750, "This PDF has embedded metadata for testing.")
c.save()

# 2. Footer/header metadata
p = os.path.join(test_dir, "footer_meta.pdf")
c = canvas.Canvas(p)
c.drawString(100, 800, "First Page Header")
c.drawString(100, 100, "Journal of Testing | Vol. 5, No. 2")
c.drawString(100, 80,  "Author: Alice Smith")
c.save()

# 3. Minimal content for AI fallback
p = os.path.join(test_dir, "ai_meta.pdf")
c = canvas.Canvas(p)
c.drawString(100, 750, "AI Fallback Article")
c.drawString(100, 730, "No embedded metadata or standard headers.")
c.save()

print("Created test PDFs in:", test_dir)
