from flask import Flask, render_template, request, jsonify
import pyautogui
import pyperclip
import logging
import time
import ctypes
import socket
import threading
import webbrowser

from werkzeug.serving import make_server

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/type', methods=['POST'])
def type_text():
    try:
        data = request.get_json()
        text = data.get('text', '')
        mode = data.get('mode', 'type')

        if not text and mode == 'type':
            return jsonify({'success': False, 'error': 'No text provided'}), 400

        if mode == 'type':
            logger.info(f"Injecting text via Clipboard: {text[:50]}...")
            pyperclip.copy(text)
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            logger.info('Injected successfully')
        elif mode == 'clipboard':
            pyperclip.copy(text)

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/key', methods=['POST'])
def press_key():
    try:
        data = request.get_json()
        key = data.get('key', '')

        if key == 'ctrl_enter':
            pyautogui.hotkey('ctrl', 'enter')
        else:
            key_map = {
                'enter': 'enter',
                'tab': 'tab',
                'backspace': 'backspace',
                'esc': 'esc',
                'space': 'space',
            }
            actual_key = key_map.get(key.lower(), key.lower())
            pyautogui.press(actual_key)

        logger.info(f"Simulated Key: {key}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def get_local_ip():
    local_ip = 'localhost'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    return local_ip


def show_message(title, text):
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
    except Exception:
        logger.warning('%s: %s', title, text)


class FlaskServerThread(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True)
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def create_tray_image():
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(47, 158, 68))
    draw.rectangle((18, 18, 46, 46), outline=(255, 255, 255), width=4)
    return image


def run_with_tray(host, port):
    if pystray is None or Image is None:
        show_message('EasyType', '缺少 pystray/pillow，无法显示托盘图标。请先执行 uv sync。')
        app.run(host=host, port=port, debug=False)
        return

    try:
        server_thread = FlaskServerThread(host, port)
    except OSError:
        show_message('EasyType', f'端口 {port} 已被占用。可能已有实例在运行。')
        return

    server_thread.start()

    local_ip = get_local_ip()
    url = f'http://{local_ip}:{port}'
    logger.info('EasyType running at: %s', url)

    def on_open(_icon, _item):
        webbrowser.open(url)

    def on_exit(icon, _item):
        logger.info('Exiting EasyType...')
        server_thread.shutdown()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem('Open', on_open),
        pystray.MenuItem('Exit', on_exit),
    )
    icon = pystray.Icon('EasyType', create_tray_image(), 'EasyType', menu)
    icon.run()


def main():
    run_with_tray(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
