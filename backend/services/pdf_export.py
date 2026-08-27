# PDF Logic with Jinja2 templates and xhtml2pdf fallback
import io
import logging

logger = logging.getLogger('ats_resume_scorer')

def generate_combined_pdf(html_docs: dict[str, str]) -> bytes:
    """Generate PDF from rendered HTML documents (WeasyPrint with xhtml2pdf fallback)."""
    try:
        from weasyprint import HTML
        documents = []
        for name, html_str in html_docs.items():
            doc = HTML(string=html_str).render()
            documents.append(doc)
        
        first_doc = documents[0]
        for other_doc in documents[1:]:
            for page in other_doc.pages:
                first_doc.pages.append(page)
                
        return first_doc.write_pdf()
    except (ImportError, Exception) as e:
        logger.warning(f"WeasyPrint PDF generation unavailable or failed: {e}. Falling back to xhtml2pdf.")
        try:
            from xhtml2pdf import pisa
            combined_html = '<pdf:nextpage />'.join(html_docs.values())
            result = io.BytesIO()
            status = pisa.CreatePDF(combined_html, dest=result)
            if status.err:
                logger.warning(f"xhtml2pdf returned status error code: {status.err}")
            return result.getvalue()
        except Exception as fallback_err:
            logger.error(f"Both WeasyPrint and xhtml2pdf failed: {fallback_err}")
            raise RuntimeError(f"PDF generation failed: {fallback_err}") from fallback_err