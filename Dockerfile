FROM odoo:18.0
USER root
# signxml for SUNAT XMLDSig signing; lxml/cryptography/requests already in image
# pin signxml 3.x: 5.x forces cryptography>=45 which conflicts with the image's debian cryptography 41
RUN pip3 install --no-cache-dir --break-system-packages "signxml==3.2.2"
USER odoo
