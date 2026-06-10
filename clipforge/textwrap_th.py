"""Thai-aware subtitle line wrapping.

Thai script has no inter-word spaces, so libass cannot semantically wrap it on its
own — even with wrap_unicode (libunibreak), the Unicode Line Breaking Algorithm
breaks between nearly any two graphemes, which is visually wrong for subtitles.

The industry-standard fix is to tokenize the text into words and insert hard line
breaks (`\\N`) at word boundaries. We use PyThaiNLP's `newmm` engine (dict-based
maximal matching) — fast, no ML deps, accurate enough for subtitle word boundaries.
"""

from pythainlp.tokenize import word_tokenize

# python-ass writes the dialogue text verbatim. ASS treats the literal two-char
# sequence  \  N  as a hard line break. In Python source that's "\\N".
ASS_LINE_BREAK = r"\N"


def wrap_thai(text: str,
              max_chars_per_line: int,
              max_lines: int = 3,
              engine: str = "newmm") -> str:
    """
    Tokenize Thai `text` and pack tokens into lines of <= max_chars_per_line,
    joining lines with the ASS \\N escape. Each line fits the width budget
    strictly — no overflow. `max_lines` is a soft cap: if content requires
    more lines, the wrap grows vertically rather than horizontally overflowing
    (an overflowing line cannot fit and would be cut off by libass anyway).

    A single token longer than max_chars_per_line is placed on its own line
    (it will overflow but cannot be split — pythainlp tokens are whole words).

    Returns the original text if it already fits on one line, if tokenization
    fails, or if max_chars_per_line is <= 0 (disabled).
    """
    if max_chars_per_line <= 0 or not text or not text.strip():
        return text
    if len(text) <= max_chars_per_line and ASS_LINE_BREAK not in text:
        return text

    try:
        tokens = word_tokenize(text, engine=engine, keep_whitespace=True)
    except Exception:
        return text
    if not tokens:
        return text

    lines: list[str] = []
    current = ""
    for tok in tokens:
        if not tok:
            continue
        candidate = current + tok
        if len(candidate.strip()) <= max_chars_per_line or not current.strip():
            current = candidate
        else:
            lines.append(current.strip())
            current = tok
    if current.strip():
        lines.append(current.strip())

    if len(lines) <= 1:
        return text
    if len(lines) > max_lines:
        # Log via caller; we still return ALL lines because truncating loses speech.
        # If this happens frequently, the user should: (a) lower font_size, or
        # (b) tighten resegment_max_duration so source segments are shorter.
        pass
    return ASS_LINE_BREAK.join(lines)


def split_into_timed_lines(text: str,
                           whisper_words: list[dict],
                           seg_start: float, seg_end: float,
                           max_chars_per_line: int,
                           target_cps: float = 30.0,
                           min_dur: float = 0.83,
                           max_dur: float = 2.5,
                           inter_gap: float = 0.08,
                           lead_time: float = 0.0,
                           anchor_to_whisper_words: bool = True,
                           max_drift_correction: float = 1.0,
                           engine: str = "newmm") -> list[dict]:
    """
    Split a transcript segment into single-line subtitle events with industry-
    standard timing (Netflix min 5/6 s, short-form max ~2.5 s).

    Algorithm (Option D — reading-rate uniform pacing):
      1. Tokenize with PyThaiNLP, greedy-pack into lines ≤ max_chars_per_line.
      2. For each line, natural_duration = chars / target_cps.
      3. Clamp each duration to [min_dur, max_dur].
      4. Cumulative start times from seg_start, separated by inter_gap.
      5. If total < seg_dur, leave trailing silence (host paused / demoing).
         If total > seg_dur, allow slight overlap into next segment — better than
         flicker. The next segment's events will start at their own seg_start.

    Whisper's word-level timestamps are intentionally NOT used: they extend the
    last token through silence, producing 4+ second holds on single words.

    The `whisper_words` arg is kept for API stability but is unused — pure
    reading-rate timing relies only on `text` and (seg_start, seg_end).
    """
    if max_chars_per_line <= 0 or not text.strip():
        return [{"text": text, "start": seg_start, "end": seg_end}]

    try:
        tokens = word_tokenize(text, engine=engine, keep_whitespace=True)
    except Exception:
        return [{"text": text, "start": seg_start, "end": seg_end}]
    tokens = [t for t in tokens if t]
    if not tokens:
        return [{"text": text, "start": seg_start, "end": seg_end}]

    # ── Greedy-pack tokens into single lines ≤ max_chars_per_line ──
    line_texts: list[str] = []
    line_buf: list[str] = []
    line_chars = 0
    for tok in tokens:
        tok_clean = tok.replace(" ", "")
        tok_n = len(tok_clean)
        if line_buf and (line_chars + tok_n) > max_chars_per_line:
            line_texts.append("".join(line_buf).strip())
            line_buf = []
            line_chars = 0
        line_buf.append(tok)
        line_chars += tok_n
    if line_buf:
        line_texts.append("".join(line_buf).strip())

    line_texts = [t for t in line_texts if t]
    if not line_texts:
        return [{"text": text, "start": seg_start, "end": seg_end}]

    # ── Compute clamped durations from reading rate ──
    target_cps = max(1.0, target_cps)
    min_dur    = max(0.1, min_dur)
    max_dur    = max(min_dur, max_dur)

    durations = []
    for ln in line_texts:
        n_chars  = max(1, len(ln.replace(" ", "")))
        nat_dur  = n_chars / target_cps
        clamped  = max(min_dur, min(max_dur, nat_dur))
        durations.append(clamped)

    # ── Per-line char-offset (within whitespace-stripped segment text) ──
    # Used to look up the Whisper word that aligns to each line's first character.
    line_char_offsets = []
    cum = 0
    for ln in line_texts:
        line_char_offsets.append(cum)
        cum += len(ln.replace(" ", ""))

    # ── Build the (char_offset → time) anchor table from Whisper words ──
    # Whisper words for Thai are sub-syllabic units; their `start` is reliable,
    # `end` extends through silence so we only consume `start`. We only anchor when
    # Whisper's text and the segment's text are roughly the same length (cleanup may
    # have shifted things a few chars; we tolerate up to 10%).
    text_stripped = text.replace(" ", "")
    anchor_table: list[tuple[int, float]] = []
    if anchor_to_whisper_words and whisper_words:
        word_chars_total = "".join(w.get("word", "") for w in whisper_words).replace(" ", "")
        tolerance = max(5, int(0.10 * len(text_stripped)))
        if abs(len(word_chars_total) - len(text_stripped)) <= tolerance:
            cum_chars = 0
            for w in whisper_words:
                wlen = len(w.get("word", "").replace(" ", ""))
                if wlen > 0:
                    anchor_table.append((cum_chars, float(w["start"])))
                cum_chars += wlen

    def lookup_anchor(char_offset: int) -> float | None:
        """Return the start time of the Whisper word covering the given char offset."""
        if not anchor_table:
            return None
        best = anchor_table[0][1]
        for off, t in anchor_table:
            if off <= char_offset:
                best = t
            else:
                break
        return best

    # ── Assign per-line start/end with anchoring + drift cap ──
    result = []
    cursor = max(0.0, seg_start - lead_time)
    for txt, dur, char_off in zip(line_texts, durations, line_char_offsets):
        cumulative_start = cursor if result else max(0.0, seg_start - lead_time)
        anchor = lookup_anchor(char_off)

        if anchor is not None and anchor > cumulative_start:
            # Host paused mid-segment. Honor the silence but cap at max_drift_correction
            # so we don't open arbitrarily long blank windows.
            gap = min(anchor - cumulative_start, max_drift_correction)
            line_start = cumulative_start + gap
        else:
            line_start = cumulative_start

        line_end = line_start + dur
        result.append({"text": txt, "start": round(line_start, 3), "end": round(line_end, 3)})
        cursor = line_end + inter_gap

    return result


def reconcile_event_timing(events: list[dict],
                           inter_gap: float = 0.08,
                           min_dur: float = 0.83) -> list[dict]:
    """
    Cross-segment cleanup pass: ensure events don't overlap each other.
    When one segment's last event overshoots into the next segment's first event,
    truncate the overshooting event to leave `inter_gap` before the next one.
    Drops events that would shrink below `min_dur` after truncation (would flicker).
    """
    if not events:
        return events
    out = [dict(events[0])]
    for ev in events[1:]:
        prev = out[-1]
        if ev["start"] < prev["end"] + inter_gap:
            # Truncate the previous event so it ends `inter_gap` before this one starts
            new_prev_end = ev["start"] - inter_gap
            if new_prev_end - prev["start"] >= min_dur:
                prev["end"] = round(new_prev_end, 3)
            else:
                # Previous would be too short — keep it as-is and push current later
                ev = dict(ev)
                ev["start"] = round(prev["end"] + inter_gap, 3)
                if ev["end"] - ev["start"] < min_dur:
                    ev["end"] = round(ev["start"] + min_dur, 3)
        out.append(dict(ev))
    return out


def auto_max_chars(font_size_px: int, frame_width_px: int,
                   margin_horizontal_px: int = 0,
                   char_width_ratio: float = 0.32) -> int:
    """
    Estimate a sensible max chars/line from font and frame metrics.
    char_width_ratio is the average rendered Thai char width as a fraction of
    font_size. Empirical for Noto Sans Thai Bold: ~0.5 — Thai diacritics inflate
    Python `len()` without consuming horizontal space, so the effective per-char
    width is well under font_size. Measured against the reference video.
    """
    if font_size_px <= 0 or frame_width_px <= 0:
        return 0
    avail = max(0, frame_width_px - 2 * margin_horizontal_px)
    char_w = max(1, int(font_size_px * char_width_ratio))
    return max(6, avail // char_w)
