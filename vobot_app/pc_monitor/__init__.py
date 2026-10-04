import lvgl as lv
import time

NAME = "PC Monitor"
CAN_BE_AUTO_SWITCHED = True

DEFAULT_URL = "http://10.0.10.12:8088/status"
POLL_SECONDS = 15

GREEN = lv.color_hex(0x00C853)
RED = lv.color_hex(0xFF3300)
ORANGE = lv.color_hex(0xFFA500)
WHITE = lv.color_hex(0xFFFFFF)
GREY = lv.color_hex(0x9E9E9E)

app_mgr = None
scr = None
header = None
summary = None
rows = None
footer = None
last_poll = 0


def get_settings_json():
    return {
        "title": "PC Monitor",
        "form": [
            {
                "type": "input",
                "default": DEFAULT_URL,
                "caption": "Status URL (DNS machine)",
                "name": "status_url",
                "attributes": {"maxLength": 100, "placeholder": DEFAULT_URL},
            },
        ],
    }


def _status_url():
    try:
        cfg = (app_mgr.config() if app_mgr else None) or {}
        return cfg.get("status_url") or DEFAULT_URL
    except Exception:
        return DEFAULT_URL


async def on_boot(apm):
    global app_mgr
    app_mgr = apm


def _build_ui():
    global scr, header, summary, rows, footer
    scr = lv.obj()
    scr.set_style_bg_color(lv.color_hex(0x000000), 0)
    scr.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

    header = lv.label(scr)
    header.set_text("PC Monitor")
    header.set_style_text_font(lv.font_ascii_bold_22, 0)
    header.set_style_text_color(WHITE, 0)
    header.align(lv.ALIGN.TOP_LEFT, 8, 6)

    summary = lv.label(scr)
    summary.set_text("...")
    summary.set_style_text_font(lv.font_ascii_bold_22, 0)
    summary.set_style_text_color(GREY, 0)
    summary.align(lv.ALIGN.TOP_RIGHT, -8, 6)

    rows = lv.obj(scr)
    rows.set_size(320, 180)
    rows.align(lv.ALIGN.TOP_LEFT, 0, 36)
    rows.set_style_bg_opa(lv.OPA.TRANSP, 0)
    rows.set_style_border_width(0, 0)
    rows.set_style_pad_all(4, 0)
    rows.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    rows.set_style_pad_row(2, 0)

    footer = lv.label(scr)
    footer.set_text("Connecting...")
    footer.set_style_text_font(lv.font_ascii_14, 0)
    footer.set_style_text_color(GREY, 0)
    footer.align(lv.ALIGN.BOTTOM_LEFT, 8, -4)

    lv.scr_load(scr)


def _show_error(msg):
    summary.set_text("!")
    summary.set_style_text_color(ORANGE, 0)
    footer.set_text(msg)


def _render(data):
    rows.clean()
    comps = data.get("computers", [])
    online, total = data.get("online", 0), data.get("total", 0)

    summary.set_text("%d/%d" % (online, total))
    if total == 0:
        summary.set_style_text_color(ORANGE, 0)
    else:
        summary.set_style_text_color(GREEN if online == total else RED, 0)

    # Down hosts first so problems are visible without scrolling
    comps = sorted(comps, key=lambda c: (c.get("up", False), c.get("name", "")))
    for c in comps:
        up = c.get("up", False)
        lbl = lv.label(rows)
        lbl.set_width(304)
        lbl.set_long_mode(lv.label.LONG.DOT)
        lbl.set_style_text_font(lv.font_ascii_18, 0)
        lbl.set_style_text_color(GREEN if up else RED, 0)
        lbl.set_text("%s %-9s %s" % ("UP  " if up else "DOWN", c.get("name", "?"), c.get("description", "")))

    err = data.get("error")
    if err:
        footer.set_text(err)
    else:
        t = time.localtime()
        footer.set_text("Updated %02d:%02d:%02d" % (t[3], t[4], t[5]))


def _poll():
    try:
        import net
        if not net.connected():
            _show_error("No Wi-Fi")
            return
    except Exception:
        pass
    try:
        import urequests
        r = urequests.get(_status_url(), timeout=3)
        try:
            data = r.json()
        finally:
            r.close()
        _render(data)
    except Exception as e:
        _show_error("Server unreachable: %s" % e)


async def on_start():
    global last_poll
    _build_ui()
    if app_mgr:
        app_mgr.enter_root_page()
    last_poll = 0


async def on_running_foreground():
    global last_poll
    now = time.time()
    if now - last_poll >= POLL_SECONDS:
        last_poll = now
        _poll()


async def on_stop():
    global scr, header, summary, rows, footer
    if scr:
        scr.clean()
    scr = header = summary = rows = footer = None
