namespace DancePlatform.API.Models;

public class VideoSegment
{
    public int Id { get; set; }
    public string Label { get; set; } = string.Empty;
    public int StartTime { get; set; }
    public int? EndTime { get; set; }

    public int VideoId { get; set; }
    public Video Video { get; set; } = null!;

    // --- Provenance -------------------------------------------------------
    // How this chip was produced and how much we trust it. The chip pipeline
    // (scripts/chip_*.py) only replaces a video's segments when its new score
    // beats the recorded Confidence — so without these a re-run would happily
    // trample better work. "manual" is never overwritten, whatever it scores.
    //
    //   chapters   adopted from the video's own chapter markers
    //   transcript inferred from speech
    //   visual     inferred from sampled frames
    //   slice      a montage window; one chip is correct by construction
    //   generic    proportional/placeholder filler, the tier to replace first
    //   legacy     predates provenance, attribution unknown
    //   manual     entered by hand through the admin form
    //
    // Deliberately absent from VideoSegmentDto: this is pipeline bookkeeping,
    // not something the player needs.
    public string? Source { get; set; }
    public float? Confidence { get; set; }
    public string? Model { get; set; }
    public DateTime? GeneratedAt { get; set; }
}
