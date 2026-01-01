# =====================================
# Dream Stack App – BG Removal + Rotate + Manual Crop
# =====================================

# =========================
# CONFIG (must be first)
# =========================
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')  # Disable red touch dots

# =========================
# KIVY IMPORTS
# =========================
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.core.image import Image as CoreImage

# =========================
# PYTHON / IMAGE IMPORTS
# =========================
from PIL import Image as PILImage
from rembg import remove
from io import BytesIO
import os
import threading

# =========================
# PATHS & CONSTANTS
# =========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JEWELRY_BOX = os.path.join(SCRIPT_DIR, "jewelry_box")
os.makedirs(JEWELRY_BOX, exist_ok=True)

MAX_SIZE = (800, 800)
ROT_STEP = 1  # degrees per click

# =====================================
# Draggable + resizable crop rectangle
# =====================================
class CropRectangle(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rect_pos = [100, 100]
        self.rect_size = [300, 300]
        self.dragging = False
        self.resizing = None
        self.last_touch = (0, 0)
        self.handle_size = 20

        with self.canvas:
            Color(1, 1, 1, 1)  # WHITE rectangle
            self.line = Line(rectangle=(*self.rect_pos, *self.rect_size), width=2)

    def get_handles(self):
        x, y = self.rect_pos
        w, h = self.rect_size
        hs = self.handle_size
        return {
            "move": (x, y, w, h),
            "left": (x - hs, y, hs, h),
            "right": (x + w, y, hs, h),
            "bottom": (x, y - hs, w, hs),
            "top": (x, y + h, w, hs),
            "bl": (x - hs, y - hs, hs, hs),
            "br": (x + w, y - hs, hs, hs),
            "tl": (x - hs, y + h, hs, hs),
            "tr": (x + w, y + h, hs, hs),
        }

    def on_touch_down(self, touch):
        for name, (hx, hy, hw, hh) in self.get_handles().items():
            if hx <= touch.x <= hx + hw and hy <= touch.y <= hy + hh:
                if name == "move":
                    self.dragging = True
                else:
                    self.resizing = name
                self.last_touch = touch.pos
                return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        dx = touch.x - self.last_touch[0]
        dy = touch.y - self.last_touch[1]

        if self.dragging:
            self.rect_pos[0] += dx
            self.rect_pos[1] += dy
        elif self.resizing:
            x, y = self.rect_pos
            w, h = self.rect_size

            if "left" in self.resizing:
                self.rect_pos[0] += dx
                self.rect_size[0] -= dx
            if "right" in self.resizing:
                self.rect_size[0] += dx
            if "bottom" in self.resizing:
                self.rect_pos[1] += dy
                self.rect_size[1] -= dy
            if "top" in self.resizing:
                self.rect_size[1] += dy

        self.last_touch = touch.pos
        self.update_graphics()
        return True

    def on_touch_up(self, touch):
        self.dragging = False
        self.resizing = None
        return super().on_touch_up(touch)

    def update_graphics(self):
        self.line.rectangle = (*self.rect_pos, *self.rect_size)

# =====================================
# MAIN APP
# =====================================
class DreamStackApp(App):
    def build(self):
        self.layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        self.upload_btn = Button(text="Upload Bangle Image", size_hint_y=None, height=50)
        self.upload_btn.bind(on_press=self.open_file_picker)
        self.layout.add_widget(self.upload_btn)

        return self.layout

    # -------------------------
    # File chooser
    # -------------------------
    def open_file_picker(self, _):
        chooser = FileChooserIconView(filters=["*.png", "*.jpg", "*.jpeg"])
        select = Button(text="Select", size_hint_y=None, height=40)

        box = BoxLayout(orientation="vertical")
        box.add_widget(chooser)
        box.add_widget(select)

        popup = Popup(title="Choose Image", content=box, size_hint=(0.9, 0.9))
        select.bind(on_press=lambda _: self.select_image(chooser.selection, popup))
        popup.open()

    def select_image(self, selection, popup):
        if not selection:
            return
        popup.dismiss()
        self.status = Label(text="Removing background...")
        self.layout.add_widget(self.status)

        threading.Thread(target=self.process_image, args=(selection[0],), daemon=True).start()

    # -------------------------
    # Background removal
    # -------------------------
    def process_image(self, path):
        try:
            img = PILImage.open(path).convert("RGBA")
            img.thumbnail(MAX_SIZE)

            out = remove(img, alpha_matting=True,
                         alpha_matting_foreground_threshold=240,
                         alpha_matting_background_threshold=10,
                         alpha_matting_erode_size=10)
            if not isinstance(out, PILImage.Image):
                out = PILImage.fromarray(out)

            output_path = os.path.join(JEWELRY_BOX, "bangle_no_bg.png")
            out.save(output_path)

            buf = BytesIO()
            out.save(buf, format="PNG")
            buf.seek(0)

            # Show rotation screen first
            Clock.schedule_once(lambda dt: self.show_rotation_screen(buf, out.size))

        except Exception as e:
            Clock.schedule_once(lambda dt: self.status.__setattr__("text", f"Failed: {e}"))

    # ==============================
    # NEW: ROTATION SCREEN
    # ==============================
    def show_rotation_screen(self, buf, img_size):
        self.layout.clear_widgets()
        self.rotation_angle = 0

        self.current_pil_image = PILImage.open(os.path.join(JEWELRY_BOX, "bangle_no_bg.png"))

        self.rot_layout = FloatLayout()
        self.layout.add_widget(self.rot_layout)

        # Display image
        self.kivy_image = KivyImage(texture=CoreImage(buf, ext="png").texture,
                                    allow_stretch=True, keep_ratio=True)
        self.kivy_image.size_hint = (1, 1)
        self.rot_layout.add_widget(self.kivy_image)

        # Fixed + sign at center
        with self.kivy_image.canvas:
            Color(1, 1, 1, 1)
            Line(points=[self.kivy_image.width/2 - 20, self.kivy_image.height/2,
                         self.kivy_image.width/2 + 20, self.kivy_image.height/2], width=2)
            Line(points=[self.kivy_image.width/2, self.kivy_image.height/2 - 20,
                         self.kivy_image.width/2, self.kivy_image.height/2 + 20], width=2)

        # Rotate buttons
        left_btn = Button(text="<-", size_hint=(0.1, 0.1), pos_hint={"x":0.05, "y":0.85})
        right_btn = Button(text="->", size_hint=(0.1, 0.1), pos_hint={"x":0.85, "y":0.85})
        left_btn.bind(on_press=lambda _: self.rotate_image(-ROT_STEP))
        right_btn.bind(on_press=lambda _: self.rotate_image(ROT_STEP))
        self.rot_layout.add_widget(left_btn)
        self.rot_layout.add_widget(right_btn)

        # Done button
        done_btn = Button(text="Done", size_hint=(0.2, 0.1), pos_hint={"center_x":0.5, "y":0.02})
        done_btn.bind(on_press=lambda _: self.open_crop_screen())
        self.rot_layout.add_widget(done_btn)

    # -------------------------
    # Rotate PIL + refresh Kivy image
    # -------------------------
    def rotate_image(self, degrees):
        self.rotation_angle += degrees
        rotated = self.current_pil_image.rotate(self.rotation_angle, expand=True)
        buf = BytesIO()
        rotated.save(buf, format="PNG")
        buf.seek(0)
        self.kivy_image.texture = CoreImage(buf, ext="png").texture

    # ==============================
    # CROP SCREEN
    # ==============================
    def open_crop_screen(self):
        self.layout.clear_widgets()
        buf = BytesIO()
        self.current_pil_image.save(buf, format="PNG")
        buf.seek(0)

        # Image
        self.kivy_image = KivyImage(texture=CoreImage(buf, ext="png").texture,
                                    allow_stretch=True, keep_ratio=True)
        self.kivy_image.size_hint = (1, 1)

        # Crop rectangle
        self.crop_rect = CropRectangle()

        # Container
        container = FloatLayout()
        container.add_widget(self.kivy_image)
        container.add_widget(self.crop_rect)

        # Crop button
        save_btn = Button(text="Crop & Save", size_hint=(0.3, 0.1), pos_hint={"center_x":0.5, "y":0.02})
        save_btn.bind(on_press=lambda _: self.crop_and_save())
        self.layout.add_widget(container)
        self.layout.add_widget(save_btn)

        # Back button to rotation
        back_btn = Button(text="Back", size_hint=(0.2, 0.1), pos_hint={"x":0.02, "y":0.02})
        back_btn.bind(on_press=lambda _: self.show_rotation_screen(
            buf=BytesIO(self.current_pil_image.tobytes()),
            img_size=self.current_pil_image.size
        ))
        self.layout.add_widget(back_btn)

    # -------------------------
    # Apply crop
    # -------------------------
    def crop_and_save(self):
        img_w, img_h = self.current_pil_image.size
        disp_w, disp_h = self.kivy_image.size
        disp_x, disp_y = self.kivy_image.pos

        rx, ry = self.crop_rect.rect_pos
        rw, rh = self.crop_rect.rect_size

        scale_x = img_w / disp_w
        scale_y = img_h / disp_h

        left = max(0, int((rx - disp_x) * scale_x))
        bottom = max(0, int((ry - disp_y) * scale_y))
        right = min(img_w, int((rx + rw - disp_x) * scale_x))
        top = min(img_h, int((ry + rh - disp_y) * scale_y))

        cropped = self.current_pil_image.crop((left, bottom, right, top))
        save_path = os.path.join(JEWELRY_BOX, "bangle_cropped.png")
        cropped.save(save_path)

        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="✅ Cropped & saved successfully", font_size=20))
        print("Saved:", save_path)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    DreamStackApp().run()
