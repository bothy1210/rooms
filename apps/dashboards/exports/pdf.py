"""
PDF report builder (WeasyPrint).

Renders an HTML template to PDF so reports reuse the same styling as the web
pages. WeasyPrint is imported lazily inside the function so the rest of the app
(and the test suite) runs even on machines where its native libraries aren't
installed — only generating a PDF requires them.
"""
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone


def build_utilisation_pdf(context: dict) -> HttpResponse:
    """Return an HttpResponse containing a utilisation report PDF."""
    from weasyprint import HTML  # lazy import — see module docstring

    html = render_to_string("reports/utilisation_pdf.html", {
        **context,
        "generated_at": timezone.now(),
    })
    pdf_bytes = HTML(string=html).write_pdf()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    stamp = timezone.now().strftime("%Y%m%d")
    response["Content-Disposition"] = f'attachment; filename="uz-room-utilisation-{stamp}.pdf"'
    return response
