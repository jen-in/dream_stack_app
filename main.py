# main.py
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage

from PIL import Image as PILImage
from rembg import remove
from io import BytesIO
import os
import threading

# Folder to save background-removed images
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JEWELRY_BOX = os.path.join(SCRIPT_DIR, "jewelry_box")

# Ensure folder exists
if os.path.exists(JEWELRY_BOX):
    if not os.path.isdir(JEWELRY_BOX):
        os.remove(JEWELRY_BOX)
        os.makedirs(JEWELRY_BOX)
else:
    os.makedirs(JEWELRY_BOX)

MAX_SIZE = (800, 800)  # Max size for processing to prevent huge images

class DreamStackApp(App):
    def build(self):
        self.main_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        upload_button = Button(text="Upload Bangle Image", font_size=20, size_hint_y=None, height=50)
        upload_button.bind(on_press=self.open_file_picker)
        self.main_layout.add_widget(upload_button)

        return self.main_layout

    def open_file_picker(self, instance):
        layout = BoxLayout(orientation='vertical')

        self.filechooser = FileChooserIconView(filters=["*.png", "*.jpg", "*.jpeg"])

        back_btn = Button(text="Back", size_hint_y=None, height=40)
        back_btn.bind(on_press=lambda x: self.go_back())

        select_btn = Button(text="Select File", size_hint_y=None, height=40)
        select_btn.bind(on_press=lambda x: self.select_file())

        layout.add_widget(back_btn)
        layout.add_widget(self.filechooser)
        layout.add_widget(select_btn)

        self.popup = Popup(title="Select a Bangle Image", content=layout, size_hint=(0.9, 0.9))
        self.popup.open()

    def go_back(self):
        self.filechooser.path = os.path.dirname(self.filechooser.path)

    def select_file(self):
        selection = self.filechooser.selection
        if selection:
            input_path = selection[0]
            self.popup.dismiss()

            self.processing_label = Label(text="Processing image, please wait...", font_size=18, size_hint_y=None, height=30)
            self.main_layout.add_widget(self.processing_label)

            threading.Thread(target=self.process_image, args=(input_path,)).start()

    def process_image(self, input_path):
        try:
            output_path = os.path.join(JEWELRY_BOX, os.path.basename(input_path).split('.')[0] + "_no_bg.png")

            # Open image
            img = PILImage.open(input_path)

            # Resize if too large
            img.thumbnail(MAX_SIZE)

            # Remove background
            output_img = remove(img)

            # Convert to PIL Image if needed
            if not isinstance(output_img, PILImage.Image):
                output_img = PILImage.fromarray(output_img)

            # Save output
            output_img.save(output_path)
            print(f"Saved PNG without background: {output_path}")

            # Convert to bytes buffer for Kivy
            buf = BytesIO()
            output_img.save(buf, format='PNG')
            buf.seek(0)

            # Schedule adding KivyImage on main thread
            Clock.schedule_once(lambda dt: self.show_preview(buf))

        except Exception as e:
            print(f"Failed to process image: {e}")
            Clock.schedule_once(lambda dt: self.show_failed_label(str(e)))

    def show_preview(self, buf):
        if hasattr(self, 'processing_label'):
            self.main_layout.remove_widget(self.processing_label)

        preview = KivyImage()
        preview.texture = CoreImage(buf, ext='png').texture
        self.main_layout.add_widget(preview)

    def show_failed_label(self, error_msg):
        if hasattr(self, 'processing_label'):
            self.main_layout.remove_widget(self.processing_label)
        fail_label = Label(text=f"Failed: {error_msg}", color=(1,0,0,1), font_size=18, size_hint_y=None, height=30)
        self.main_layout.add_widget(fail_label)


if __name__ == "__main__":
    DreamStackApp().run()
