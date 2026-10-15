import lvgl as lv
import time

NAME = "PC Monitor"
CAN_BE_AUTO_SWITCHED = True

DEFAULT_URL = "http://10.0.10.12:8088/status"
POLL_SECONDS = 15
ROW_HEIGHT = 24
COLUMN_WIDTHS = (52, 92, 152)

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
    """Return the web settings form for the status service URL."""
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
    """Return the configured status URL, falling back to the default."""
    try:
        cfg = (app_mgr.config() if app_mgr else None) or {}
        return cfg.get("status_url") or DEFAULT_URL
    except Exception:
        return DEFAULT_URL


async def on_boot(apm):
    """Save the application manager used to read persistent settings."""
    global app_mgr
    app_mgr = apm


def _column(parent, text, width, color):
    """Create a fixed-width, truncated text cell and return its label."""
    label = lv.label(parent)
    label.set_width(width)
    label.set_long_mode(lv.label.LONG.DOT)
    label.set_style_text_font(lv.font_ascii_18, 0)
    label.set_style_text_color(color, 0)
    label.set_text(text)
    return label


def _table_row(parent):
    """Return a transparent 304-pixel row with evenly spaced columns."""
    row = lv.obj(parent)
    row.set_size(304, ROW_HEIGHT)
    row.set_style_bg_opa(lv.OPA.TRANSP, 0)
    row.set_style_border_width(0, 0)
    row.set_style_pad_all(0, 0)
    row.set_style_pad_column(4, 0)
    row.set_flex_flow(lv.FLEX_FLOW.ROW)
    row.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return row


def _on_key(event):
    """Scroll one row per encoder step; leave other keys to the system."""
    if rows is None:
        return
    key = event.get_key()
    if key == lv.KEY.LEFT:
        rows.scroll_by(0, -ROW_HEIGHT, lv.ANIM.OFF)
    elif key == lv.KEY.RIGHT:
        rows.scroll_by(0, ROW_HEIGHT, lv.ANIM.OFF)


def _build_ui():
    """Build the fixed header/footer and vertically scrollable host table."""
    global scr, header, summary, rows, footer
    scr = lv.obj()
    scr.set_style_bg_color(lv.color_hex(0x000000), 0)
    scr.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    scr.remove_flag(lv.obj.FLAG.SCROLLABLE)
    scr.add_event_cb(_on_key, lv.EVENT.KEY, None)

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

    headings = _table_row(scr)
    headings.align(lv.ALIGN.TOP_LEFT, 8, 34)
    for text, width in zip(("State", "Name", "Description"), COLUMN_WIDTHS):
        label = _column(headings, text, width, GREY)
        label.set_style_text_font(lv.font_ascii_14, 0)

    rows = lv.obj(scr)
    rows.set_size(320, 158)
    rows.align(lv.ALIGN.TOP_LEFT, 0, 56)
    rows.set_style_bg_opa(lv.OPA.TRANSP, 0)
    rows.set_style_border_width(0, 0)
    rows.set_style_pad_all(0, 0)
    rows.set_style_pad_left(8, 0)
    rows.set_style_pad_right(8, 0)
    rows.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    rows.set_style_pad_row(0, 0)
    rows.set_scroll_dir(lv.DIR.VER)
    rows.set_scrollbar_mode(lv.SCROLLBAR_MODE.AUTO)
    rows.remove_flag(lv.obj.FLAG.SCROLL_ELASTIC)

    footer = lv.label(scr)
    footer.set_text("Connecting...")
    footer.set_style_text_font(lv.font_ascii_14, 0)
    footer.set_style_text_color(GREY, 0)
    footer.set_width(304)
    footer.set_long_mode(lv.label.LONG.DOT)
    footer.align(lv.ALIGN.BOTTOM_LEFT, 8, -4)

    lv.scr_load(scr)


def _show_error(msg):
    """Display an error message while retaining the last computer list."""
    summary.set_text("!")
    summary.set_style_text_color(ORANGE, 0)
    footer.set_text(msg)


def _render(data):
    """Render status data and retain the scroll offset within the new bounds."""
    scroll_y = rows.get_scroll_y()
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
        row = _table_row(rows)
        color = GREEN if up else RED
        values = ("UP" if up else "DOWN", c.get("name", "?"), c.get("description", ""))
        for text, width in zip(values, COLUMN_WIDTHS):
            _column(row, text, width, color)

    rows.update_layout()
    max_scroll = max(0, rows.get_scroll_y() + rows.get_scroll_bottom())
    rows.scroll_to_y(min(max(0, scroll_y), max_scroll), lv.ANIM.OFF)

    err = data.get("error")
    if err:
        footer.set_text(err)
    else:
        t = time.localtime()
        footer.set_text("Updated %02d:%02d:%02d" % (t[3], t[4], t[5]))


def _poll():
    """Fetch status with a three-second timeout and always close the response."""
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
    """Create the foreground UI and schedule an immediate status poll."""
    global last_poll
    _build_ui()
    if app_mgr:
        app_mgr.enter_root_page()
    last_poll = 0


async def on_running_foreground():
    """Poll status only when the configured interval has elapsed."""
    global last_poll
    now = time.time()
    if now - last_poll >= POLL_SECONDS:
        last_poll = now
        _poll()


async def on_stop():
    """Clear UI objects and references safely, including on repeated stops."""
    global scr, header, summary, rows, footer
    if scr:
        scr.clean()
    scr = header = summary = rows = footer = None
