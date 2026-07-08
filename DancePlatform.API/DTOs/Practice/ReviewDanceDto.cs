namespace DancePlatform.API.DTOs.Practice;

/// <summary>A learned dance that has gone unpracticed long enough to be due for review.</summary>
public class ReviewDanceDto
{
    public int DanceId { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;
    public string StyleName { get; set; } = string.Empty;
    public string? ThumbnailVideoId { get; set; }
    public string? ThumbnailPlatform { get; set; }

    /// <summary>Local date of the last meaningful practice; null if never practiced since tracking began.</summary>
    public DateOnly? LastPracticedOn { get; set; }

    /// <summary>Days since the dance was last touched (practiced, or marked learned if more recent).</summary>
    public int DaysSince { get; set; }
}
