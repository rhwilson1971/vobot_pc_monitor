# Scrollable computer columns

Approved design: fixed Status, Name, and Description columns on the 320x240
display. Keep title, column headings, and footer outside the scrolling list.
Use encoder key events to scroll one row at a time and preserve the vertical
offset across refreshes, clamping when the list shrinks. Keep DOWN hosts first.

Implementation steps:
- Add fixed-width label and row helpers to the dock entrypoint.
- Configure a vertical viewport, column headings, and screen key handler.
- Restore the scroll offset after rendering, and document all touched functions.
- Delete the obsolete push script; retain the DNS service.
- Update README and project guidance to remove obsolete references.
- Verify syntax, whitespace, layout dimensions, key handling, refresh clamping,
  empty data, and repeated cleanup using a lightweight LVGL stand-in. Physical
  rendering and encoder focus still require a dock check.
