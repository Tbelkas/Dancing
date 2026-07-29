namespace DancePlatform.API.DTOs.Roadmap;

/// <summary>A roadmap as it appears on the index — no stages, just the shape and the user's progress.</summary>
public class RoadmapSummaryDto
{
    public int Id { get; set; }
    public string Slug { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Subtitle { get; set; } = string.Empty;
    public string? Description { get; set; }

    public int StyleId { get; set; }
    public string StyleName { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;

    public int StageCount { get; set; }
    public int StepCount { get; set; }

    /// <summary>Steps that resolve to a catalog move — the ones that can be marked learned.</summary>
    public int MoveCount { get; set; }

    /// <summary>Videos available across every linked move, for the viewer.</summary>
    public int VideoCount { get; set; }

    /// <summary>Of <see cref="MoveCount"/>, how many the current user has marked learned (0 when anonymous).</summary>
    public int LearnedCount { get; set; }
    public int InProgressCount { get; set; }

    public string? ThumbnailVideoId { get; set; }
    public string? ThumbnailPlatform { get; set; }
}

/// <summary>The full path: every stage with its steps, each step carrying its move and videos.</summary>
public class RoadmapDto : RoadmapSummaryDto
{
    public List<RoadmapStageDto> Stages { get; set; } = new();
}

public class RoadmapStageDto
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public List<RoadmapStepDto> Steps { get; set; } = new();
}

public class RoadmapStepDto
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }

    /// <summary>Null when the catalog has no move for this step yet.</summary>
    public RoadmapStepDanceDto? Dance { get; set; }
}

/// <summary>
/// The catalog move behind a step. Deliberately narrower than <c>DanceDto</c> — a path needs the
/// link, the status toggles, and the videos, not the full browse-card payload.
/// </summary>
public class RoadmapStepDanceDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;
    public string Difficulty { get; set; } = string.Empty;
    public double AverageRating { get; set; }
    public int RatingCount { get; set; }
    public bool IsLearned { get; set; }
    public bool IsInProgress { get; set; }
    public bool IsFavorite { get; set; }
    public List<RoadmapStepVideoDto> Videos { get; set; } = new();
}

public class RoadmapStepVideoDto
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string VideoId { get; set; } = string.Empty;
    public string Platform { get; set; } = string.Empty;
    public string VideoType { get; set; } = string.Empty;
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }
    public int? DurationSeconds { get; set; }
    public long ViewCount { get; set; }
    public double AverageRating { get; set; }
    public int RatingCount { get; set; }
}
