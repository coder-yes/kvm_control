import tkinter as tk
import cv2
from PIL import Image, ImageTk
from pynput import keyboard
import serial
import queue
import threading
import serial.tools.list_ports
from tkinter import ttk
import configparser
import numpy as np


key_dict = {
    "1": 0x1E,
    "2": 0x1F,
    "3": 0x20,
    "4": 0x21,
    "5": 0x22,
    "6": 0x23,
    "7": 0x24,
    "8": 0x25,
    "9": 0x26,
    "0": 0x27,
    "a": 0x04,
    "b": 0x05,
    "c": 0x06,
    "d": 0x07,
    "e": 0x08,
    "f": 0x09,
    "g": 0x0A,
    "h": 0x0B,
    "i": 0x0C,
    "j": 0x0D,
    "k": 0x0E,
    "l": 0x0F,
    "m": 0x10,
    "n": 0x11,
    "o": 0x12,
    "p": 0x13,
    "q": 0x14,
    "r": 0x15,
    "s": 0x16,
    "t": 0x17,
    "u": 0x18,
    "v": 0x19,
    "w": 0x1A,
    "x": 0x1B,
    "y": 0x1C,
    "z": 0x1D,
    "f1": 0x3A,
    "f2": 0x3B,
    "f3": 0x3C,
    "f4": 0x3D,
    "f5": 0x3E,
    "f6": 0x3F,
    "f7": 0x40,
    "f8": 0x41,
    "f9": 0x42,
    "f10": 0x43,
    "f11": 0x44,
    "f12": 0x45,
    "enter": 0x28,
    "esc": 0x29,
    "backspace": 0x2A,
    "tab": 0x2B,
    "space": 0x2C,
    "printscreen": 0x46,
    "home": 0x4A,
    "delete": 0x4C,
    "end": 0x4D,
    "right": 0x4F,
    "left": 0x50,
    "down": 0x51,
    "up": 0x52,
    "esc": 0x29,
    "ctrl": 0xE0,
    "shift": 0xE1,
    "alt": 0xE2,
    "cmd": 0xE3,
    "-": 0x2D,
    "=": 0x2E,
    "[": 0x2F,
    "]": 0x30,
    "\\\\": 0x31,
    "'": 0x34,
    ";": 0x33,
    "`": 0x35,
    ",": 0x36,
    ".": 0x37,
    "/": 0x38,
    "page_up": 0x4B,
    "page_down": 0x4E,
    "caps_lock": 0x39,
    "insert": 0x49,
}


lclick_down_command = [0x57, 0xAB, 0x00, 0x05, 0x05, 0x01, 0x01, 0x00, 0x00, 0x00, 0x0E]
rclick_down_command = [0x57, 0xAB, 0x00, 0x05, 0x05, 0x01, 0x02, 0x00, 0x00, 0x00, 0x0F]
click_up_command = [0x57, 0xAB, 0x00, 0x05, 0x05, 0x01, 0x00, 0x00, 0x00, 0x00, 0x0D]
key_up_command = [
    0x57,
    0xAB,
    0x00,
    0x02,
    0x08,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x0C,
]
recover_key_mouse_command = click_up_command + key_up_command

default_width = 1920
default_height = 1080


def generate_mouse_move_command(x, y, mouse_value):
    x_pos = int((x * 4096) / default_width)
    y_pos = int((y * 4096) / default_height)

    x_low = x_pos & 0xFF
    x_high = (x_pos >> 8) & 0xFF

    y_low = y_pos & 0xFF
    y_high = (y_pos >> 8) & 0xFF

    command = [
        0x57,
        0xAB,
        0x00,
        0x04,
        0x07,
        0x02,
        mouse_value,
        x_low,
        x_high,
        y_low,
        y_high,
        0x00,
    ]
    command.append(sum(command) & 0xFF)
    return command


class VideoCaptureApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.keyboard_listener = (
            None  # the tkinter cannot suppress the key to OS, so use pynput instead.
        )
        self.ser = None
        self.video_capture = None
        self.default_frame = (
            np.ones((default_height, default_width, 3), dtype=np.uint8) * 100
        )
        self.put_text_center(self.default_frame, "No Video detected")
        self.key_mouse_cmd_queue = queue.Queue()
        self.key_mouse_cmd_write_thread = threading.Thread(
            target=self.key_mouse_cmd_routine
        )
        self.key_mouse_cmd_write_thread.start()

        self.key_mouse_passthrough = True
        self.combine_key = 0x00
        self.mouse_x = 0
        self.mouse_y = 0

        # Configuration file setup
        self.config_file = "config.ini"

        self.canvas = tk.Canvas(window, width=default_width, height=default_height)
        # Create a frame to contain the comboboxes
        self.control_pannel_frame = tk.Frame(window)
        self.control_pannel_frame.pack(side=tk.TOP, padx=10, pady=10)

        self.canvas.pack()

        self.canvas.bind("<Motion>", self.on_mouse_event)
        self.canvas.bind("<Button-1>", self.on_mouse_event)
        self.canvas.bind("<Button-3>", self.on_mouse_event)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_event)
        self.canvas.bind("<ButtonRelease-3>", self.on_mouse_event)
        self.canvas.bind("<Enter>", self.on_enter_canvas)
        self.canvas.bind("<Leave>", self.on_leave_canvas)
        self.canvas.bind("<MouseWheel>", self.on_mouse_event)

        self.camera_label = ttk.Label(self.window, text="Camera:")
        self.camera_label.pack(side=tk.LEFT, padx=5)
        self.available_cameras = self.get_available_cameras()
        self.selected_camera = tk.StringVar()
        default_camera_index = self.load_config("camera_index")
        if default_camera_index in self.available_cameras:
            self.selected_camera.set(default_camera_index)
        elif self.available_cameras:
            self.selected_camera.set(self.available_cameras[0])
        self.camera_combobox = ttk.Combobox(
            self.window,
            textvariable=self.selected_camera,
            values=self.available_cameras,
            state="readonly",
        )
        self.camera_combobox.pack(side=tk.LEFT)
        self.camera_combobox.bind("<<ComboboxSelected>>", self.open_selected_camera)
        if self.camera_combobox.get():
            self.camera_combobox.event_generate("<<ComboboxSelected>>")
        else:
            print("No camera selected to trigger")

        self.com_port_label = ttk.Label(self.window, text="Key&Mouse:")
        self.com_port_label.pack(side=tk.LEFT, padx=5)
        self.available_com_ports = self.get_available_com_ports()
        self.selected_com_port = tk.StringVar()
        default_com_port = self.load_config("comport")
        if default_com_port in self.available_com_ports:
            self.selected_com_port.set(default_com_port)
        else:
            self.selected_com_port.set(
                self.available_com_ports[0]
            )  # Default to the first available COM port
        self.com_port_combobox = ttk.Combobox(
            self.window,
            textvariable=self.selected_com_port,
            values=self.available_com_ports,
            state="readonly",
        )
        self.com_port_combobox.pack(side=tk.LEFT)
        self.com_port_combobox.bind("<<ComboboxSelected>>", self.open_selected_com_port)
        if self.com_port_combobox.get():
            self.com_port_combobox.event_generate("<<ComboboxSelected>>")
        else:
            print("No com port selected to trigger")

        self.btn_capture = tk.Button(
            window, text="Capture Image", command=self.capture_image
        )
        self.btn_capture.pack(side=tk.LEFT, padx=5)

        self.btn_start_stop = tk.Button(window, command=self.toggle_monitoring)
        self.btn_start_stop.pack(side=tk.LEFT, padx=5)
        self.toggle_monitoring()

        self.delay = 10
        self.update()

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.window.mainloop()

    def save_config(self, key, value, segment="default"):
        config = configparser.ConfigParser()
        config.read(self.config_file)
        if not config.has_section(segment):
            config.add_section(segment)
        config.set(segment, key, str(value))
        with open(self.config_file, "w") as configfile:
            config.write(configfile)

    def load_config(self, key, segment="default"):
        config = configparser.ConfigParser()
        config.read(self.config_file)
        if config.has_option(segment, key):
            return config.get(segment, key)
        else:
            return None

    def get_available_cameras(self):
        available_cameras = []
        for i in range(0, 10):  # Check up to index 9
            capture = cv2.VideoCapture(i)
            if capture.isOpened():
                capture.release()
                available_cameras.append(str(i))
        return available_cameras

    def open_selected_camera(self, event=None):
        try:
            selected_camera = int(self.selected_camera.get())

            self.video_capture = cv2.VideoCapture(selected_camera, cv2.CAP_DSHOW)
            if not self.video_capture.isOpened():
                raise ValueError(f"Unable to open camera {selected_camera}")

            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, default_width)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, default_height)
            print(f"Camera {selected_camera} opened successfully.")
            self.save_config("camera_index", selected_camera)
        except ValueError as ve:
            print(f"ValueError: {ve}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def get_available_com_ports(self):
        com_ports = [port.device for port in serial.tools.list_ports.comports()]
        if not com_ports:
            com_ports = [""]
        return com_ports

    def open_selected_com_port(self, event=None):
        selected_port = self.selected_com_port.get()
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            if selected_port:
                self.ser = serial.Serial(selected_port, 9600, timeout=1)
                print(f"Serial port {selected_port} opened successfully.")
                self.save_config("comport", selected_port)
        except serial.SerialException as e:
            print(f"Error opening serial port {selected_port}: {e}")

    def update(self):
        frame = self.default_frame
        if self.video_capture and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
        original_height, original_width = frame.shape[:2]
        new_width = original_width // 2
        new_height = original_height // 2
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        height, width, _ = frame.shape
        self.canvas.config(width=width, height=height)  # config it when changed.
        self.photo = ImageTk.PhotoImage(
            image=Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        )
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        self.window.after(self.delay, self.update)

    def put_text_center(
        self,
        image,
        text,
        font=cv2.FONT_HERSHEY_SIMPLEX,
        font_scale=1,
        color=(255, 255, 255),
        thickness=2,
    ):
        # Get the text size
        text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
        text_width, text_height = text_size

        # Calculate the position for the text to be centered
        text_x = (image.shape[1] - text_width) // 2
        text_y = (image.shape[0] + text_height) // 2

        # Put the text on the image
        cv2.putText(image, text, (text_x, text_y), font, font_scale, color, thickness)

    def capture_image(self):
        if self.video_capture and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                cv2.imwrite("captured_image.bmp", frame)
                print("Image Captured Successfully!")

    def on_mouse_event(self, event):
        if not self.key_mouse_passthrough:
            return
        if event.type == tk.EventType.Motion:
            self.mouse_x = self.canvas.canvasx(event.x)
            self.mouse_y = self.canvas.canvasy(event.y)
            self.key_mouse_cmd_queue.put(
                generate_mouse_move_command(2 * self.mouse_x, 2 * self.mouse_y, 0x00)
            )
        elif event.type == tk.EventType.ButtonPress:
            if event.num == 1:
                self.key_mouse_cmd_queue.put(lclick_down_command)
            if event.num == 3:
                self.key_mouse_cmd_queue.put(rclick_down_command)
                # print(f"{event.num} mouse button clicked at (x, y): {self.mouse_x}, {self.mouse_y}")
        elif event.type == tk.EventType.ButtonRelease:
            self.key_mouse_cmd_queue.put(click_up_command)
            # print(f"{event.num} mouse button released at (x, y): {self.mouse_x}, {self.mouse_y}")
        elif event.type == tk.EventType.MouseWheel:
            if event.delta > 0:
                self.key_mouse_cmd_queue.put(
                    [0x57, 0xAB, 0x00, 0x05, 0x05, 0x01, 0x00, 0x00, 0x00, 0x01, 0x0E]
                )
                # print("Mouse wheel scrolled up")
            else:
                self.key_mouse_cmd_queue.put(
                    [0x57, 0xAB, 0x00, 0x05, 0x05, 0x01, 0x00, 0x00, 0x00, 0xFF, 0x0C]
                )
                # print("Mouse wheel scrolled down")

    def toggle_monitoring(self):
        self.key_mouse_passthrough = not self.key_mouse_passthrough
        if self.key_mouse_passthrough:
            self.btn_start_stop.config(text="Mode(Passthrough)", bg="red")
        else:
            self.btn_start_stop.config(text="Mode(Read Only)", bg="SystemButtonFace")

    def key_mouse_cmd_routine(self):
        while True:
            item = self.key_mouse_cmd_queue.get()
            if item is None:
                break
            if self.ser and self.ser.is_open:
                self.ser.write(item)
            self.key_mouse_cmd_queue.task_done()

    def generate_key_down_command(self, character, combine_key):
        if character not in key_dict:
            return []
        data = [
            0x57,
            0xAB,
            0x00,
            0x02,
            0x08,
            combine_key,
            0x00,
            key_dict[character],
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
        data.append(sum(data) & 0xFF)
        return data

    def start_monitor_keyboard(self):
        def on_press(key):
            try:
                pass
                # print('Mouse Coordinates (x, y):', self.mouse_x, self.mouse_y)
                # print('Key Pressed:', key.char)
            except AttributeError:
                pass
                # print('Special key pressed:', key)
            keystr = (
                str(key)
                .strip("'")
                .strip('"')
                .removeprefix("Key.")
                .removesuffix("_l")
                .removesuffix("_r")
                .removesuffix("_gr")
            )
            if "ctrl" in keystr:
                self.combine_key = self.combine_key | 0x01
            if "shift" in keystr:
                self.combine_key = self.combine_key | 0x02
            if "alt" in keystr:
                self.combine_key = self.combine_key | 0x04
            if "cmd" in keystr:
                self.combine_key = self.combine_key | 0x08
            key_cmd = self.generate_key_down_command(keystr, self.combine_key)
            self.key_mouse_cmd_queue.put(key_cmd)
            print(keystr)
            print(key_cmd)

        def on_release(key):
            keystr = (
                str(key)
                .strip("'")
                .strip('"')
                .removeprefix("Key.")
                .removesuffix("_l")
                .removesuffix("_r")
                .removesuffix("_gr")
            )
            if "ctrl" in keystr:
                self.combine_key = self.combine_key & ~0x01
            if "shift" in keystr:
                self.combine_key = self.combine_key & ~0x02
            if "alt" in keystr:
                self.combine_key = self.combine_key & ~0x04
            if "cmd" in keystr:
                self.combine_key = self.combine_key & ~0x08
            self.key_mouse_cmd_queue.put(key_up_command)
            print("Release", key)

        self.combine_key = 0x00  # consider it as nonlocal.
        self.keyboard_listener = keyboard.Listener(
            on_press=on_press, on_release=on_release, suppress=True
        )
        self.keyboard_listener.start()

    def stop_monitor_keyboard(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def on_close(self):
        self.stop_monitor_keyboard()
        self.key_mouse_cmd_queue.put(recover_key_mouse_command)
        self.key_mouse_cmd_queue.put(None)
        self.key_mouse_cmd_write_thread.join()
        if self.ser and self.ser.is_open:
            self.ser.close()
        if self.video_capture and self.video_capture.isOpened():
            self.video_capture.release()
        self.window.destroy()

    def on_enter_canvas(self, event):
        if not self.key_mouse_passthrough:
            return
        self.window.config(cursor="none")  # Hide the cursor
        self.start_monitor_keyboard()

    def on_leave_canvas(self, event):
        if not self.key_mouse_passthrough:
            return
        self.window.config(cursor="")  # Show the cursor
        self.stop_monitor_keyboard()
        self.key_mouse_cmd_queue.put(recover_key_mouse_command)


# Create a window and pass it to the VideoCaptureApp class
VideoCaptureApp(tk.Tk(), "OpenCV Video Capture")
