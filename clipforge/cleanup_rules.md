# Thai Transcript Cleanup — Agent Rules

**Purpose:** Correct obvious Whisper STT errors in Thai fitness video transcripts.
**Source:** faster-whisper large-v3 (CPU, int8) — known to mis-transcribe ~5–10% of characters in fast colloquial Thai speech.
**Last Updated:** 2026-06-03

---

## Hard rules (never break)

1. **Preserve meaning.** Only correct when you are highly confident the original is a STT error AND the correction is what the speaker actually said. When in doubt, return the original unchanged.
2. **Preserve Thai script.** Never transliterate, romanise, or translate.
3. **Preserve filler particles** the speaker actually used: `นะครับ`, `ค่ะ`, `น่ะ`, `เลย`. Do not strip them — they're part of the natural speech style.
4. **Preserve loan words** the speaker used in English (e.g. `support`, `function`, `set`). Keep them as English — don't force-translate to Thai.
5. **Do not invent content.** If a phrase is garbled and you can't confidently reconstruct it, leave it as-is. Better to leave a typo than to invent the wrong word.
6. **Do not change punctuation, capitalization, or spacing patterns** beyond fixing actual errors.

---

## Common Whisper Thai error patterns (look for these)

### 1. Tone-mark errors
Whisper often picks the wrong tone mark because it requires very accurate prosody capture. Common confusions:
- ่ (mai ek) vs ้ (mai tho) vs ๊ (mai tri) vs ๋ (mai chattawa)
- Example: `เนี้ย` is rare; `เนี่ย` is the common conversational particle. Prefer `เนี่ย` when the context is informal.
- Example: `ก้าว` (step, common) vs `กาว` (glue, rare in fitness)

### 2. Sara Am normalisation
Whisper sometimes outputs the decomposed form `ํา` (NIKHAHIT + SARA AA) instead of the precomposed `ำ` (SARA AM).
- `ทํา` → `ทำ`
- `จํา` → `จำ`
- `นํา` → `นำ`
Apply this normalisation whenever you see it.

### 3. Sound-alike consonant substitutions
Thai has many consonants that share sounds. Whisper sometimes picks the wrong one:
- บ (b) / ป (p) — both are unaspirated stops
- ด (d) / ต (t)
- ก (k) / ข (kh) / ค (kh)
- Example: `บ่าย` (afternoon) vs `ปวด` (pain) — in a fitness context, expect `ปวด`/`เจ็บ` (pain), not `บ่าย`.

### 4. English loan-word mis-spelling
Whisper may transcribe loan words as phonetic Thai or mis-spell the English:
- `suport` → `support`
- `set` (rep set) — usually kept as English
- `function` / `functional` — sometimes Thai-ised as `ฟังก์ชัน` / `ฟังก์ชันนัล`
Pick whichever form fits the surrounding context (mostly Thai → use Thai form; mostly English → keep English).

### 5. Compound-word boundary errors
Whisper sometimes splits compounds incorrectly:
- `กล้ามเนื้อ` (muscle) is one word — not `กล้าม เนื้อ`
- `ส้นเท้า` (heel) is one word
- `หน้าขา` (front of thigh / quad) is one word
- `หัวเข่า` (knee) is one word

### 6. Spelling errors that produce non-words
If Whisper output contains a string that is not a real Thai word and there's an obvious near-miss real word, correct it.
- `อับ` (rare/unusual) at the start of a fitness instruction likely → `จับ` (grip) or `ขับ` (drive) depending on context.

---

## Fitness-context vocabulary (likely correct in this domain)

Body parts: `กล้ามเนื้อ`, `ขา`, `แขน`, `หลัง`, `หน้าท้อง`, `ก้น`, `ส้นเท้า`, `หัวเข่า`, `ข้อเท้า`, `สะโพก`, `หน้าขา`, `น่อง`, `ไหล่`

Actions/positions: `กระชับ`, `ยืด`, `งอ`, `ตรง`, `หมุน`, `กด`, `ก้าว`, `ลุก`, `นั่ง`, `ยืน`, `ลง`, `ยก`, `บิด`

Quantifiers: `ครับ`, `นะครับ`, `เลย`, `เนี่ย`, `แบบนี้`, `เหมือน`, `แล้วก็`, `ซึ่ง`

Common phrases: `ลงน้ำหนัก` (put weight on), `ห่วงยาง` (love handles), `กดส้นเท้า` (press heel), `แข็งแรง` (strong), `ฟอร์ม` (form), `เทรนนิ่ง` (training)

---

## Output contract

Return ONLY this JSON shape, no markdown fences, no preamble:

```json
{
  "corrections": [
    {
      "index": 3,
      "original": "บ่ายเจ็บ",
      "corrected": "ปวดเจ็บ",
      "confidence": "high",
      "reason": "fitness context — 'pain' makes sense, 'afternoon' does not"
    }
  ],
  "notes": "1-2 sentence summary of what kinds of errors you fixed"
}
```

`confidence`: `"high"`, `"medium"`, or `"low"`.
- `high` — clearly wrong + clearly right correction
- `medium` — likely wrong, plausible correction
- `low` — possibly wrong, uncertain correction (caller may discard these)

Only include segments that need correction. If nothing needs correction, return `{"corrections": [], "notes": "transcript looks clean"}`.
