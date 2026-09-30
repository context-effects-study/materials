# Survey walkthrough

`SURVEY_WALKTHROUGH.pdf` shows every distinct screen of the five confirmatory surveys as a participant sees
it, one section per survey with a caption per screen; the 32 screenshots are in
`png/`. Each screen was rendered on September 29, 2026 from the survey files in `../out/`, filled with a real
participant script, in a web browser: the question text and page code exactly as in the survey files, the
pictures from `../png/`, and the page layout of Qualtrics. The placeholder consent text and completion code
are described in `../README.md`. The confirmatory surveys have no comprehension items; the attention check is
their only check question.

One difference from the survey files in `../out/`: since the screens were rendered, the surveys print every
price of a constructed option with two decimals ($41.50 where a screen shows $41.5). No value changed; only
the way a price ending in a zero cent is printed.
