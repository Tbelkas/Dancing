namespace DancePlatform.API.Models;

/// <summary>One leg of a <see cref="Roadmap"/> — a themed group of steps ("Find the pulse").</summary>
public class RoadmapStage
{
    public int Id { get; set; }

    public int RoadmapId { get; set; }
    public Roadmap Roadmap { get; set; } = null!;

    public string Title { get; set; } = string.Empty;

    /// <summary>What this stage is for, in a sentence.</summary>
    public string? Description { get; set; }

    public int SortOrder { get; set; }

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public List<RoadmapStep> Steps { get; set; } = new();
}
