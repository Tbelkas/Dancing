"""
Tests for the intake gate's decision logic.

    python -m pytest scripts/test_gate_logic.py -q

No database, no network, no GPU: every test here builds a row dict or a transcript
string by hand and checks what the code decides about it.

WHY THESE EXIST
---------------
Five bugs shipped into this pipeline in one day, and all five were the same shape - a
check that reported success while measuring nothing:

  1. progress measured on the wall clock, so a 6-hour machine sleep read as work
  2. silent transcripts counted as evidence coverage
  3. a filter reading a column its query never SELECTed, so every row was None
  4. a prefix match against a comma-separated list, so "silent" third in the list missed
  5. the Intake tab omitting live videos the frames had condemned

None of them raised. None of them produced an empty result that looked wrong. In every
case working and broken were indistinguishable from outside, which is precisely why
they need tests rather than care.

So the tests below are deliberately weighted towards "does this SURFACE the thing it is
supposed to surface", not just "does it reject the thing it is supposed to reject". A
rule that catches nothing passes every rejection test ever written.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import verify_intake as vi   # noqa: E402
import verify_visual as vv   # noqa: E402
import video_gate as vg      # noqa: E402


# --------------------------------------------------------------- name matching

@pytest.mark.parametrize("dance,text,expected", [
    ("Loose Legs", "Loose Legs (House Dance Tutorials) Fullout", True),
    # One substitution; both spellings are in real use for this style.
    ("Waacking", "How To Whack | Beginner Whacking Tutorial", True),
    # A space, which toks() cannot see because "dance" is a stop word.
    ("Breakdance", "10 Easy Break Dance TOPROCKS for Beginners", True),
    # Genuinely different moves must still be caught - the point of the whole check.
    ("Tendu", "Plie Combination - Level 1", False),
    ("Blade", "Learn How To Backspin | Power Move Basics", False),
    # Same move under a different name: string comparison cannot know this, and the
    # test records that limitation rather than pretending it is handled.
    ("Dramatic Dip", "Learn How to Death Drop - Inside Drag", False),
])
def test_name_matches(dance, text, expected):
    assert vg.name_matches(dance, text) is expected


# ---------------------------------------------------------- dance vocabulary

SMASH = ("Hey guys, it's Ken. I'm doing a Dancing Blade guide with SSBM tutorials. "
         "Dancing Blade is the name of Marth's ForwardB. First, before we start this "
         "Dancing Blade tutorial, let's categorize the sword dances into three "
         "different speeds. The first two hits, you can always mash, but after that "
         "it takes some timing, and he swings forward across.")

CHARLESTON = ("The Tandem Charleston in Lindy Hop. So from closed position, just like "
              "we would start for the swingout, we're going to take the rock step, and "
              "instead of doing a triple step, we're going to do our Charleston step. "
              "rock step, kick, step back. The rock steps one, two. one, two, kick "
              "three, step down four, five, pull up six, reach seven, come back eight.")

BUS_STOP = ("I'm going to show you the bus stop. So we're going to start with the right "
            "leg, you kick and you cross at the same time, going back now. Two, three, "
            "four, left leg again back, five, going forward, six, seven, together. "
            "Right leg tap, one, two, three, four, click the heels.")


def test_smash_bros_guide_is_not_a_dance_video():
    """The canonical impostor: names the move, is instructional, is not dancing."""
    ok, core, gen = vi.talks_like_dancing(SMASH)
    assert not ok
    assert core == 0, "generic motion verbs must not earn CORE credit"


def test_swing_tutorial_passes():
    """Lindy's whole vocabulary is rock step / triple step / kick / swingout. When
    those sat in GENERIC this scored CORE 0 and was rejected outright."""
    ok, core, _ = vi.talks_like_dancing(CHARLESTON)
    assert ok and core >= 2


def test_counting_teacher_passes():
    """ASR writes counts interleaved with words, so the fixed phrases never match."""
    ok, _, _ = vi.talks_like_dancing(BUS_STOP)
    assert ok


def test_empty_transcript_is_not_evidence_of_anything():
    """Non-English audio transcribes to near-nothing under an English-only model.
    Rejecting on that would condemn the catalogue's non-English half."""
    ok, core, gen = vi.talks_like_dancing("")
    assert not ok
    assert core + gen < 3, "must fall in the 'unclear' band, not the reject band"


# --------------------------------------------------- what reaches the reviewer

def _row(**kw):
    r = {"vid": 1, "ytid": "x" * 11, "platform": "youtube", "vtype": "tutorial",
         "title": "T", "clipstart": None, "dur": 300, "views": 100,
         "state": "approved", "qflags": None, "qnote": None,
         "dance": "Test Move", "styles": "House", "otherdances": 0}
    r.update(kw)
    return r


@pytest.mark.parametrize("flags,should_show", [
    # The bug: the rubric scores a silent video 1.0 ("admit"), the row is live, so
    # both of the original tests passed and a condemned video appeared nowhere.
    ("visual:not-a-dance-video,has-onscreen-text", True),
    ("visual:dance-performance", True),
    ("visual:dance-but-other-move", True),
    # A video that turned out fine is not a decision anyone needs to make.
    ("visual:teaches-this-move,has-onscreen-text", False),
    ("visual:cannot-tell", False),
])
def test_live_video_condemned_by_frames_reaches_intake(flags, should_show):
    """Mirrors the surfacing rule in chip_ui.intake_rows."""
    r = _row(qflags=flags)
    score, verdict, _, _ = vg.grade(r)
    assert verdict == "admit", "fixture must be one the rubric would pass, or it proves nothing"

    stored = r["qflags"] or ""
    seen_and_bad = any(stored.startswith(f"visual:{v}") for v in
                       ("not-a-dance-video", "dance-performance", "dance-but-other-move"))
    shows = r["state"] != "approved" or verdict != "admit" or seen_and_bad
    assert shows is should_show


# ------------------------------------------------------ blindness detection

@pytest.mark.parametrize("flags,expected", [
    # Bug 4: "silent" arriving third in video_gate's list was missed by a prefix match,
    # which skipped the entire population the visual pass was built for.
    ("same-clip-on-4-dances,too-short,silent", True),
    ("silent", True),
    ("unclear,core-0", True),
    ("no-transcript", True),
    # Already looked at - do not pay for frames twice.
    ("visual:teaches-this-move", False),
    ("visual:cannot-tell", False),
])
def test_blindness_is_detected_anywhere_in_the_flag_list(flags, expected, monkeypatch):
    monkeypatch.setattr(vg, "load_sig", lambda _y: None)
    monkeypatch.setattr(vv.vg, "load_sig", lambda _y: None)
    assert vv.is_blind(_row(qflags=flags)) is expected


def test_untranscribed_rows_are_left_to_the_backfill(monkeypatch):
    """No transcript is not the same as no speech. Transcription is far cheaper than a
    model call on frames, so those rows belong to the backfill first."""
    monkeypatch.setattr(vv.vg, "load_sig", lambda _y: None)
    assert vv.is_blind(_row(qflags=None)) is False


def test_a_transcript_with_no_words_counts_as_blind(monkeypatch):
    monkeypatch.setattr(vv.vg, "load_sig",
                        lambda _y: {"asr": {"segments": [{"text": "uh"}]}})
    assert vv.is_blind(_row(qflags=None)) is True


# ------------------------------------------------------------------ scoring

def test_absence_of_evidence_scores_at_the_review_boundary():
    """Silence and a failed transcript are not marks against a video. Scoring them low
    would quietly reject every wordless tutorial - a real format."""
    assert vi.VERDICT_SCORE["silent"] == pytest.approx(0.50)
    assert vi.VERDICT_SCORE["unclear"] == pytest.approx(0.50)
    assert vi.VERDICT_SCORE["no-transcript"] == pytest.approx(0.50)


def test_a_dead_video_scores_below_a_merely_wrong_one():
    """A wrong video can be reassigned to the right dance. A dead one cannot be
    anything, and the page is broken for everyone who opens it."""
    assert vi.VERDICT_SCORE["video-unavailable"] < vi.VERDICT_SCORE["not-a-dance-video"]
