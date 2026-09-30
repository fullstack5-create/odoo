"""Spanish number-to-words for SUNAT 'monto en letras' (leyenda 1000).

Handles 0..999,999,999 plus two-decimal cents as 'XX/100'. Enough for invoices.
"""

_UNITS = ['', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE',
          'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISEIS', 'DIECISIETE',
          'DIECIOCHO', 'DIECINUEVE', 'VEINTE']
_TENS = ['', '', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA',
         'OCHENTA', 'NOVENTA']
_HUNDREDS = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS',
             'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']


def _under_thousand(n):
    if n == 0:
        return ''
    if n == 100:
        return 'CIEN'
    words = []
    c, rem = divmod(n, 100)
    if c:
        words.append(_HUNDREDS[c])
    if rem:
        if rem <= 20:
            words.append(_UNITS[rem])
        elif rem < 30:
            words.append('VEINTI' + _UNITS[rem - 20])
        else:
            t, u = divmod(rem, 10)
            words.append(_TENS[t] + (' Y ' + _UNITS[u] if u else ''))
    return ' '.join(words)


def _integer_to_words(n):
    if n == 0:
        return 'CERO'
    parts = []
    millions, rem = divmod(n, 1_000_000)
    thousands, units = divmod(rem, 1000)
    if millions:
        parts.append('UN MILLON' if millions == 1 else _under_thousand(millions) + ' MILLONES')
    if thousands:
        parts.append('MIL' if thousands == 1 else _under_thousand(thousands) + ' MIL')
    if units:
        parts.append(_under_thousand(units))
    return ' '.join(p for p in parts if p)


def amount_to_words(amount, currency_name='SOLES'):
    """2360.00 -> 'DOS MIL TRESCIENTOS SESENTA CON 00/100 SOLES'."""
    amount = round(float(amount), 2)
    integer = int(amount)
    cents = int(round((amount - integer) * 100))
    return '%s CON %02d/100 %s' % (_integer_to_words(integer), cents, currency_name)
