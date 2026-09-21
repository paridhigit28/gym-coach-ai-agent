"""
Reusable presentation-layer building blocks for Trainora.

These are pure HTML/CSS render helpers — every function just returns/writes
markup via st.markdown(..., unsafe_allow_html=True). None of them touch
business logic, session state (beyond reading values passed in), the
database, or AI/model calls. Pages import what they need and keep all of
their existing Streamlit widgets and Python logic exactly as before.
"""

import base64
import html
import os
import streamlit as st


def _esc(value) -> str:
    """HTML-escape any value that gets interpolated into markup."""
    return html.escape(str(value)) if value is not None else ""


@st.cache_data(show_spinner=False)
def image_to_base64(path: str) -> str:
    """Encode a local image once (cached) so it can be embedded inline in a
    custom HTML card layout (e.g. the hero mascot), where a plain st.image
    call couldn't sit inside the flex layout."""
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def tag(label: str) -> None:
    """Small uppercase pill used at the top of every page (e.g. 'YOUR DASHBOARD')."""
    st.markdown(
        f'''
        <div class="tr-tag">
            <span class="dot"></span>
            <span>{_esc(label)}</span>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "", tag_label: str = "") -> None:
    """Standard page header: optional tag, big title, optional subtitle."""
    if tag_label:
        tag(tag_label)
    parts = [f'<div class="tr-page-header">']
    parts.append(f'<h1 class="tr-page-title">{_esc(title)}</h1>')
    if subtitle:
        parts.append(f'<p class="tr-page-subtitle">{_esc(subtitle)}</p>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def section_header(title: str, hint: str = "") -> None:
    """Divider-style header used to introduce a section within a page."""
    hint_html = f'<span class="tr-section-hint">{_esc(hint)}</span>' if hint else ""
    st.markdown(
        f'''
        <div class="tr-section-header">
            <span class="tr-section-title">{_esc(title)}</span>
            {hint_html}
        </div>
        ''',
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, unit: str = "", caption: str = "") -> None:
    """Small metric card — e.g. 'Current Weight' / '72' 'kg'."""
    unit_html = f'<span class="unit">{_esc(unit)}</span>' if unit else ""
    caption_html = f'<div class="tr-stat-caption">{_esc(caption)}</div>' if caption else ""
    st.markdown(
        f'''
        <div class="tr-stat-card">
            <div class="tr-stat-label">{_esc(label)}</div>
            <div class="tr-stat-value">{_esc(value)}{unit_html}</div>
            {caption_html}
        </div>
        ''',
        unsafe_allow_html=True,
    )


def agent_card_markup(image_b64: str, title: str, desc: str, featured: bool = False) -> str:
    """Returns the markup for an agent card (caller places the CTA button
    right below it with a normal st.button, since Streamlit interactivity
    can't live inside injected HTML). Built as a single line (no stray
    blank/indented lines) so Streamlit's markdown parser never mistakes
    part of it for an indented code block."""
    card_class = "tr-agent-card tr-agent-card-featured" if featured else "tr-agent-card"
    badge_html = '<div class="tr-agent-badge">Live</div>' if featured else ""
    img_html = (
        f'<img class="tr-agent-mascot" src="data:image/png;base64,{image_b64}" alt="" />'
        if image_b64 else ""
    )
    return (
        f'<div class="{card_class}">'
        f'{badge_html}'
        f'{img_html}'
        f'<div class="tr-agent-title">{_esc(title)}</div>'
        f'<div class="tr-agent-desc">{_esc(desc)}</div>'
        f'</div>'
    )


def agent_card(image_b64: str, title: str, desc: str, featured: bool = False) -> None:
    st.markdown(agent_card_markup(image_b64, title, desc, featured), unsafe_allow_html=True)


def hero(tag_label: str, greeting: str, sub: str) -> None:
    """Premium dashboard hero used at the top of Home."""
    st.markdown(
        f'''
        <div class="tr-hero">
            <div class="tr-hero-copy">
                <div class="tr-tag" style="margin-bottom:12px;">
                    <span class="dot"></span><span>{_esc(tag_label)}</span>
                </div>
                <div class="tr-hero-greeting">{greeting}</div>
                <div class="tr-hero-sub">{_esc(sub)}</div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "neutral") -> str:
    """Returns markup for a small status badge. kind: neutral|good|warn|bad|live."""
    dot = '<span class="dot"></span>' if kind == "live" else ""
    css_kind = kind if kind in ("good", "warn", "bad", "live") else ""
    return f'<span class="tr-badge {css_kind}">{dot}{_esc(text)}</span>'


def progress_card(title: str, pct: int, caption: str = "") -> None:
    pct = max(0, min(100, int(pct)))
    st.markdown(
        f'''
        <div class="tr-progress-card">
            <div class="tr-section-title" style="margin-bottom:2px;">{_esc(title)}</div>
            <div class="tr-progress-bar-track">
                <div class="tr-progress-bar-fill" style="width:{pct}%;"></div>
            </div>
            <div class="tr-stat-caption" style="margin-top:8px;">{_esc(caption)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def empty_state(title: str, body_html: str) -> None:
    """body_html may contain simple inline HTML (already trusted/internal)."""
    st.markdown(
        f'''
        <div class="trainora-empty-state">
            <h2>{title}</h2>
            <p>{body_html}</p>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def macro_pills(protein=None, carbs=None, fats=None) -> str:
    pills = []
    if protein is not None:
        pills.append(f'<span class="tr-macro-pill">Protein {_esc(protein)}</span>')
    if carbs is not None:
        pills.append(f'<span class="tr-macro-pill">Carbs {_esc(carbs)}</span>')
    if fats is not None:
        pills.append(f'<span class="tr-macro-pill">Fats {_esc(fats)}</span>')
    return f'<div class="tr-macro-row">{"".join(pills)}</div>'


def meal_card_head(meal_name: str, kcal) -> None:
    st.markdown(
        f'''
        <div class="tr-meal-card-head">
            <span class="tr-meal-name">{_esc(meal_name)}</span>
            <span class="tr-meal-kcal">{_esc(kcal)} kcal</span>
        </div>
        ''',
        unsafe_allow_html=True,
    )


# --- Workout planner image/card helpers integrated from Trainora 7 ---

def plan_total_bar(text_html: str) -> None:
    """Highlighted one-line summary bar used above a plan's grid (e.g.
    'Plan total: 2395 kcal · Protein 132g · ...'). text_html may contain
    simple inline tags like <b> (already trusted/internal, built from
    _esc()-ed pieces by the caller)."""
    st.markdown(f'<div class="tr-plan-total-bar">{text_html}</div>', unsafe_allow_html=True)


def dish_item_markup(image_src: str, name: str, meta: str = "", index=None) -> str:
    """One large tile inside a plan grid: big square demo photo on top
    (numbered when `index` is given), name, then a small meta line (e.g. a
    serving size for a meal, or 'Sets x Reps x Rest' for an exercise)."""
    img_html = (
        f'<img class="tr-dish-thumb" src="{_esc(image_src)}" alt="{_esc(name)}" loading="lazy" />'
        if image_src else '<div class="tr-dish-thumb tr-dish-thumb-empty">🏋️</div>'
    )
    num_html = f'<span class="tr-dish-num">{index}</span>' if index is not None else ""
    meta_html = f'<div class="tr-dish-meta">{_esc(meta)}</div>' if meta else ""
    return (
        '<div class="tr-dish-item">'
        f'<div class="tr-dish-thumb-wrap">{img_html}{num_html}</div>'
        f'<div class="tr-dish-name">{_esc(name)}</div>'
        f'{meta_html}'
        '</div>'
    )


def plan_grid_card_markup(
    eyebrow: str,
    title: str,
    meta_right: str,
    items_html: str,
    footnote_html: str = "",
    icon: str = "",
) -> str:
    """A card in a plan grid (a meal-type or a workout day): optional emoji
    icon + small uppercase eyebrow + bold title on the left, a highlighted
    value on the right (kcal / calories burned / a badge), a grid of
    dish_item_markup thumbnails, and an optional footnote line (macros,
    warmup/cooldown, etc)."""
    footnote = f'<div class="tr-plan-footnote">{footnote_html}</div>' if footnote_html else ""
    icon_html = f'<span class="tr-meal-icon">{_esc(icon)}</span>' if icon else ""
    return (
        '<div class="tr-meal-card">'
        '<div class="tr-meal-card-head">'
        '<div class="tr-meal-card-head-left">'
        f'{icon_html}'
        '<div>'
        f'<div class="tr-meal-eyebrow">{_esc(eyebrow)}</div>'
        f'<span class="tr-meal-name">{_esc(title)}</span>'
        '</div>'
        '</div>'
        f'<span class="tr-meal-kcal">{meta_right}</span>'
        '</div>'
        f'<div class="tr-dish-grid">{items_html}</div>'
        f'{footnote}'
        '</div>'
    )


def rest_card_markup(eyebrow: str, title: str, body: str, icon: str = "🌙") -> str:
    """Simpler, calmer card variant for a rest/off day -- no dish grid,
    just a centered icon and a short message."""
    return (
        '<div class="tr-meal-card tr-rest-card">'
        '<div class="tr-rest-icon">' + _esc(icon) + '</div>'
        f'<span class="tr-meal-name">{_esc(title)}</span>'
        f'<div class="tr-meal-eyebrow" style="margin:4px 0 14px;">{_esc(eyebrow)}</div>'
        f'{badge("Rest Day", "neutral")}'
        f'<p class="tr-rest-copy">{_esc(body)}</p>'
        '</div>'
    )


def day_notes_markup(warmup: str = "", cooldown: str = "") -> str:
    """Two-up highlighted note strip for a training day's warmup/cooldown,
    used instead of a plain footnote line so it reads as an actual part of
    the plan rather than small print."""
    if not warmup and not cooldown:
        return ""
    parts = ['<div class="tr-day-notes">']
    if warmup:
        parts.append(
            '<div class="tr-day-note">'
            '<div class="tr-day-note-head"><span class="tr-day-note-icon">🔥</span>'
            '<span class="tr-day-note-label">Warm-up</span></div>'
            f'<p>{_esc(warmup)}</p>'
            '</div>'
        )
    if cooldown:
        parts.append(
            '<div class="tr-day-note">'
            '<div class="tr-day-note-head"><span class="tr-day-note-icon">❄️</span>'
            '<span class="tr-day-note-label">Cool-down</span></div>'
            f'<p>{_esc(cooldown)}</p>'
            '</div>'
        )
    parts.append('</div>')
    return "".join(parts)


_DAY_ICON_RULES = [
    (("push", "chest", "shoulder", "triceps", "upper"), "💪"),
    (("pull", "back", "biceps", "lat"), "🏋️"),
    (("leg", "lower", "squat", "glute", "quad", "hamstring"), "🦵"),
    (("core", "ab", "plank"), "🔥"),
    (("cardio", "run", "hiit", "conditioning"), "🏃"),
    (("full body", "full-body", "total body"), "⚡"),
    (("mobility", "stretch", "yoga", "recovery"), "🧘"),
    (("rest",), "🌙"),
]


def day_icon(workout_type: str) -> str:
    """Pick a small emoji that matches a workout-day title (e.g. 'Upper
    Body Push (Chest, Shoulders, Triceps)' -> 💪) so each day is easier to
    tell apart at a glance. Falls back to a generic dumbbell."""
    t = (workout_type or "").lower()
    for keywords, icon in _DAY_ICON_RULES:
        if any(k in t for k in keywords):
            return icon
    return "🏋️"


def exercise_card_markup(name: str, sets, reps, rest, image_src: str) -> str:
    """Row used inside the workout-plan expander: exercise name + Sets/Reps/
    Rest pills on the left, a demo-image thumbnail on the right so the user
    can see how the movement is performed at a glance."""
    img_html = (
        f'<img class="tr-exercise-thumb" src="{_esc(image_src)}" alt="{_esc(name)} demo" loading="lazy" />'
        if image_src else ""
    )
    return (
        '<div class="tr-exercise-card">'
        '<div class="tr-exercise-info">'
        f'<div class="tr-exercise-row">'
        f'<span>Sets: <b>{_esc(sets or "-")}</b></span>'
        f'<span>Reps: <b>{_esc(reps or "-")}</b></span>'
        f'<span>Rest: <b>{_esc(rest or "-")}</b></span>'
        '</div>'
        '</div>'
        f'{img_html}'
        '</div>'
    )
