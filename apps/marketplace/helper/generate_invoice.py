from apps.marketplace.models import Earning,Payout
from django.http import HttpResponse
from django.template.loader import get_template
import pdfkit
import os
from django.core.files.base import ContentFile
from SF import settings
from apps.common.s3_helper import S3BucketHelper
from apps.common.urls_helper import URLHelper
url_hp = URLHelper()

def generate_pdf(user_id, payout_id=None):

    recoards = []
    if payout_id is not None:
        recoards = Earning.objects.filter(payout_id=payout_id, user_id=user_id).values(
        "payout",
        "amount",
        "job__title",
        "job__publish_content_type",
        "job__brand__brand_name",
        "milestone__milestone_number",
        )
    else:
        recoards = Earning.objects.filter(user_id=user_id).values(
        "payout",
        "amount",
        "job__title",
        "job__publish_content_type",
        "job__brand__brand_name",
        "milestone__milestone_number",
        )
    total_amount = sum(recoard["amount"] for recoard in recoards)
    context = {"recoards": recoards,"total_amount": total_amount}
    template = get_template("invoice.html")
    html = template.render(context)


    # Configure PDFkit options
    options = {
        'page-size': 'Letter',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
    }

    # Create a PDF file and write to response
    pdf = pdfkit.from_string(html, False, options=options)
    response = HttpResponse(pdf, content_type='application/pdf')
    filename="invoice_payout_id.pdf"
    response['Content-Disposition'] = 'attachment; filename=invoice_payout_id.pdf'

    pdf_file = ContentFile(response.content)

    path = f"{settings.BASE_DIR}/media/upload_invoice_Pdf/{filename}"
    with open(path, 'wb') as f:
        f.write(pdf_file.read())

    s3 = S3BucketHelper(foldername="upload_invoice_Pdf", path=path)

    if s3.upload_to_s3(filename):
        os.remove(path)
        Payout.objects.filter(id=recoards[0]["payout"]).update(
            pdf_url=f"{url_hp.AWS_CREATIVE_BASE_URL}/upload_invoice_Pdf/{filename}",
        )
    response['Content-Disposition'] = 'attachment; filename=invoice_payout_id.pdf'
    return response