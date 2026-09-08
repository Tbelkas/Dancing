namespace DancePlatform.API.DTOs.Admin;

/// <summary>
/// The catalogue's standing health: the headline counts, then one entry per thing that can rot.
///
/// Every check here already existed as a script somebody had to remember to run
/// (scripts/audit_labels.py, chip_health.py, verify_intake.py, backfill_durations.py). The point
/// of the page is that nobody has to remember.
/// </summary>
public class CatalogHealthDto
{
    public CatalogTotalsDto Totals { get; set; } = new();
    public List<HealthCheckDto> Checks { get; set; } = new();
    public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;
}

public class CatalogTotalsDto
{
    /// <summary>Dances in the public catalogue (approved).</summary>
    public int Dances { get; set; }
    /// <summary>Curated videos on the site (approved, global).</summary>
    public int Videos { get; set; }
    /// <summary>Videos the intake gate is holding back — the intake queue's depth.</summary>
    public int PendingVideos { get; set; }
    /// <summary>Videos reviewed and refused.</summary>
    public int RejectedVideos { get; set; }
    /// <summary>User-submitted dances awaiting review.</summary>
    public int PendingDances { get; set; }
    /// <summary>Open problem reports, from viewers and from the link checker.</summary>
    public int OpenFlags { get; set; }
    public int Styles { get; set; }
    public int Instructors { get; set; }
}

/// <summary>One thing that can be wrong with the catalogue, and the worst examples of it.</summary>
public class HealthCheckDto
{
    /// <summary>Stable slug — the UI keys its links and its collapse state off this, not the title.</summary>
    public string Key { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    /// <summary>Why this matters, in one line — a bare count doesn't tell you whether to act.</summary>
    public string Detail { get; set; } = string.Empty;
    public int Count { get; set; }
    /// <summary>"warn" (a reader would notice) or "info" (tidiness). Nothing here is an outage.</summary>
    public string Severity { get; set; } = "info";
    /// <summary>A sample, not the whole set — enough to start fixing, capped so the page stays fast.</summary>
    public List<HealthItemDto> Items { get; set; } = new();
}

public class HealthItemDto
{
    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
    public string DanceSlug { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;
    /// <summary>Set when the finding is about one video rather than the dance as a whole.</summary>
    public int? VideoId { get; set; }
    public string? VideoTitle { get; set; }
    /// <summary>The specific value that tripped the check, when a number says it best.</summary>
    public string? Note { get; set; }
}
