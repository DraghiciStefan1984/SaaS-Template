import csv
import html
import io
import json
from dataclasses import dataclass
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer
from rest_framework.exceptions import ValidationError

from .models import ReportFormat


@dataclass(frozen=True)
class RenderedReportArtifact:
    content: bytes
    content_type: str
    extension: str


def _json_text(content):
    return json.dumps(content, indent=2, sort_keys=True, ensure_ascii=True, default=str)


def _render_json(content):
    return RenderedReportArtifact(
        content=_json_text(content).encode("utf-8"),
        content_type="application/json",
        extension="json",
    )


def _render_csv(content):
    rows = content.get("rows") if isinstance(content, dict) else None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        rows = [
            {
                "key": key,
                "value": json.dumps(value, ensure_ascii=True, default=str)
                if isinstance(value, (dict, list))
                else value,
            }
            for key, value in (
                content.items() if isinstance(content, dict) else [("value", content)]
            )
        ]

    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames or ["value"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return RenderedReportArtifact(
        content=output.getvalue().encode("utf-8-sig"),
        content_type="text/csv; charset=utf-8",
        extension="csv",
    )


def _render_html(content, title):
    body = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Arial,sans-serif;max-width:960px;margin:40px auto;"
        "padding:0 20px;color:#17202a}pre{white-space:pre-wrap;background:#f6f8fb;"
        "border:1px solid #d8e0e8;padding:16px}</style></head><body>"
        f"<h1>{html.escape(title)}</h1><pre>{html.escape(_json_text(content))}</pre>"
        "</body></html>"
    )
    return RenderedReportArtifact(
        content=body.encode("utf-8"),
        content_type="text/html; charset=utf-8",
        extension="html",
    )


def _render_pdf(content, title):
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(output, pagesize=A4, title=title)
    story = [
        Paragraph(html.escape(title), styles["Title"]),
        Spacer(1, 12),
        Preformatted(_json_text(content), styles["Code"]),
    ]
    document.build(story)
    return RenderedReportArtifact(
        content=output.getvalue(),
        content_type="application/pdf",
        extension="pdf",
    )


def _render_docx(content, title):
    paragraphs = [title, _json_text(content)]
    document_xml = "".join(
        f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"
        for text in paragraphs
    )
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
            'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
            'officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{document_xml}<w:sectPr/></w:body></w:document>",
        )
    return RenderedReportArtifact(
        content=output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        extension="docx",
    )


def render_report_artifact(*, format, content, title):
    renderers = {
        ReportFormat.JSON: lambda: _render_json(content),
        ReportFormat.CSV: lambda: _render_csv(content),
        ReportFormat.HTML: lambda: _render_html(content, title),
        ReportFormat.PDF: lambda: _render_pdf(content, title),
        ReportFormat.DOCX: lambda: _render_docx(content, title),
    }
    renderer = renderers.get(format)
    if renderer is None:
        raise ValidationError({"format": "Unsupported report artifact format."})
    return renderer()
