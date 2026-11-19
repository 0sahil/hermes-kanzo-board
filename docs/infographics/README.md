# Header and infographics

The README's header and diagrams, as HTML.

- `how-it-works.html`: a README diagram, 1200 wide (`<W>,<H>` = `1200,760`), transparent, dark and light; crop the
  empty rows below the footer.
- `setup-flow.html`: a README diagram, 1200 wide (`<W>,<H>` = `1200,760`), transparent, dark and light; crop the
  empty rows below the footer.
- `header.html`: the README header, 1280×360 (`<W>,<H>` = `1280,360`), transparent, dark and light.

Render with any Chromium-based browser, transparent, once per theme (`#light` switches the light
colours; the README picks the image matching the reader's GitHub theme):

```sh
chrome --headless=new --hide-scrollbars --default-background-color=00000000 \
  --force-device-scale-factor=2 --window-size=<W>,<H> \
  --screenshot="$PWD/../images/<name>-dark.png" "file://$PWD/<name>.html"        # and #light → <name>-light.png
```
