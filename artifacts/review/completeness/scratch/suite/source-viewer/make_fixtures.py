"""Regenerates the small, non-sensitive PDF/DOCX/MD fixtures (run with backend/.venv/bin/python)."""
from pathlib import Path

from docx import Document

out = Path(__file__).parent / "fixtures"
pages = [
    "Meeting room booking tool - overview. The team wants one place to reserve rooms and see free slots.",
    "Requirements - page two. Reservations must send a reminder message ten minutes before the start time. Rooms are shared by three departments.",
    "Constraints - page three. No personal data is stored. The first release only needs a web form and a daily summary email.",
]
body = [b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
# object numbers: 1 catalog, 2 pages, 3 font, then (page, content) pairs starting at 4
kids = " ".join(f"{4 + i * 2} 0 R" for i in range(len(pages)))
body[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode()
for i in range(len(pages)):
    stream = f"BT /F1 11 Tf 50 750 Td ({pages[i]}) Tj ET".encode()
    body.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {5 + i * 2} 0 R /Resources << /Font << /F1 3 0 R >> >> >>".encode())
    body.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
pdf, offsets = b"%PDF-1.4\n", []
for number, content in enumerate(body, 1):
    offsets.append(len(pdf))
    pdf += f"{number} 0 obj\n".encode() + content + b"\nendobj\n"
xref = len(pdf)
pdf += f"xref\n0 {len(body) + 1}\n0000000000 65535 f \n".encode()
pdf += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
pdf += f"trailer\n<< /Size {len(body) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
(out / "booking-spec.pdf").write_bytes(pdf)

doc = Document()
for text in ["Meeting room booking - working notes.", "Rooms are booked by department assistants today, by email.",
             "Double bookings happen about twice a month.", "A reminder before each meeting would reduce no-shows.",
             "Calendar integration is optional for the first release.", "The owner of the rollout is the facilities team."]:
    doc.add_paragraph(text)
doc.save(out / "booking-notes.docx")

(out / "booking-memo.md").write_text("\n".join([
    "# Booking memo", "", "- Goal: fewer double bookings.", "- Users: about 120 employees.", "- Data: room name, time slot, organizer name.",
    "- Out of scope: catering orders.", "- Success: no double booking for one full month.", ""]), encoding="utf-8")
print("ok")
