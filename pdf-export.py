from fpdf import FPDF
import os


class PictureBook(FPDF):
    def header(self):
        # Optional: Add a title to every page or a border
        pass

    def add_book_page(self, image_path, caption=""):
        self.add_page()

        # Calculate dimensions to keep aspect ratio
        # A4 is 210mm x 297mm. We'll use a max width of 190mm.
        self.image(image_path, x=10, y=20, w=190)

        if caption:
            self.set_y(-40)  # Position 40mm from bottom
            self.set_font("Arial", 'I', 12)
            self.cell(0, 10, caption, align='C')


# Initialize
pdf = PictureBook(orientation='P', unit='mm', format='A4')
pdf.set_auto_page_break(auto=True, margin=15)

# Example: Adding images from a list or folder
images = ["cover.jpg", "page1.jpg", "page2.jpg"]

for img in images:
    # Use the filename as a caption for now, or leave blank
    caption_text = f"Illustration: {img}"
    pdf.add_book_page(img, caption=caption_text)

pdf.output("my_picture_book.pdf")
