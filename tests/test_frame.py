import json
import re

import frame


def test_confirm_in_an_arrow_handler_becomes_async():
    src = '$("#x").addEventListener("click", () => {\n  if (confirm("Delete?")) go();\n});'
    out = frame.make_async_confirm(src)
    assert 'async () => {' in out and 'await __kzConfirm("Delete?")' in out


def test_confirm_in_a_function_becomes_async():
    out = frame.make_async_confirm('function chooseSide({ first }) {\n  if (first) {\n    if (confirm("a")) x();\n  }\n}')
    assert out.startswith("async function chooseSide")


def test_already_async_functions_are_left_alone():
    out = frame.make_async_confirm('async function del() { if (!confirm("x")) return; }')
    assert out.count("async") == 1 and "await __kzConfirm" in out


def test_method_property_confirm():
    out = frame.make_async_confirm('button.onclick = () => {\n    if (confirm(tr("Update?"))) install();\n  };')
    assert "button.onclick = async () =>" in out


def test_other_confirm_names_are_untouched():
    src = "obj.confirm(1); myconfirm(2);"
    assert frame.make_async_confirm(src) == src


def test_sync_fallback_never_says_yes():
    assert frame.sync_confirm('if (confirm("x")) del();') == 'if (__kzConfirmSync("x")) del();'


def test_adapt_swaps_storage_and_hostname_only():
    out = frame.adapt('localStorage.getItem("a"); window.localStorage; x.localStorageGet(); location.hostname')
    assert out == '__kzStorage.getItem("a"); window.localStorage; x.localStorageGet(); __KZ_HOST'


def test_build_injects_base_and_bridge_and_replaces_app_js():
    index = '<!doctype html><html><head><title>Kanzo</title></head><body><div id="b"></div>\n<script src="/app.js"></script>\n</body></html>'
    html = frame.build(index, 'console.log("</script>"); if (confirm("x")) y();', "http://127.0.0.1:4242/", {"k": "v"})
    head = html.split("<title>")[0]
    assert '<base href="http://127.0.0.1:4242/">' in head
    assert "window.__KZ_CFG=" in head
    assert 'src="/app.js"' not in html
    assert "window.__kzRun = " in head  # defined by the bridge in <head> ...
    assert '<script>__kzRun()</script>\n</body>' in html  # ... and run where app.js was
    m = re.search(r"window\.__KZ_CFG=(\{.*?\});</script>", html, re.S)
    assert m is not None
    cfg = json.loads(m.group(1))
    assert cfg["base"] == "http://127.0.0.1:4242/" and cfg["storage"] == {"k": "v"}
    assert "await __kzConfirm" in cfg["asyncSource"] and "__kzConfirmSync" in cfg["syncSource"]
    # The app's own "</script>" text cannot close the config script early.
    assert html.count("</script>") == html.count("<script")


def test_build_escapes_the_base_attribute():
    html = frame.build("<html><head></head><body></body></html>", "", 'http://h:1/"><x', {})
    assert '<base href="http://h:1/&quot;><x">' in html
