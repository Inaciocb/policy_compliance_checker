from PIL import Image, ImageDraw, ImageFont

def create_sample_receipt(filename="tests/sample_receipt.png"):
    # Criar uma imagem em branco estilo cupom fiscal
    img = Image.new('RGB', (400, 500), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    # Texto do cupom fiscal fictício
    receipt_text = """
    *** HOTEL & RESTAURANT SANTA MARIA ***
    Date: 2026-09-24

    ITEMS:
    1. Room Night Standard ........ $180.00
    2. Executive Lunch ............ $25.00
    3. Craft Beer IPA 500ml ....... $10.00

    -------------------------------------
    TOTAL:                          $215.00
    -------------------------------------
    Payment Method: Credit Card
    Itemized Receipt #88912
    """

    d.text((20, 20), receipt_text, fill=(0, 0, 0))
    img.save(filename)
    print(f"Sample receipt image generated at: {filename}")

if __name__ == "__main__":
    create_sample_receipt()