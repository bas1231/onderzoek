from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

CONTENT = (
    ROOT
    / "control/browser_extension/content.js"
)


def source():
    return CONTENT.read_text(
        encoding="utf-8"
    )


def test_e415_has_task_shape_filter():
    src = source()

    assert (
        "function looksLikeExecutableTaskBlock("
        in src
    )

    assert (
        'candidate.startsWith("{")'
        in src
    )

    assert (
        '\'"task_id"\''
        in src
    )

    assert (
        '\'"task_class"\''
        in src
    )

    assert (
        '\'"operation"\''
        in src
    )


def test_e415_filters_before_json_parse():
    src = source()

    scan = src.index(
        "async function scanForTasks()"
    )

    parse = src.index(
        "JSON.parse(block)",
        scan,
    )

    gate = src.rfind(
        "looksLikeExecutableTaskBlock(",
        scan,
        parse,
    )

    assert gate > scan
    assert gate < parse


def test_e415_filters_body_fallback():
    src = source()

    start = src.index(
        "const fallbackBlocks"
    )

    section = src[
        start:
        start + 1200
    ]

    assert (
        "looksLikeExecutableTaskBlock("
        in section
    )


def test_e415_content_version():
    src = source()

    assert (
        'const CONTENT_VERSION = "0.9.1";'
        in src
    )
