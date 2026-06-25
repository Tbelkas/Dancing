namespace DancePlatform.API.DTOs.Dance;

public class DanceDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    /// <summary>Slug of the canonical style, for building the /dances/{styleSlug}/{slug} URL.</summary>
    public string StyleSlug { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; }
    public string Difficulty { get; set; } = "None";
    public List<string> Styles { get; set; } = new();
    public List<string> MusicalStyles { get; set; } = new();
    public List<string> Instructors { get; set; } = new();
    public int VideoCount { get; set; }
    public string? ThumbnailVideoId { get; set; }
    public string? ThumbnailPlatform { get; set; }
    public int FavoriteCount { get; set; }
    public int LearnedCount { get; set; }
    public double AverageRating { get; set; }
    public int RatingCount { get; set; }
    public int? UserRating { get; set; }
    public bool IsFavorite { get; set; }
    public bool IsLearned { get; set; }
    public bool IsInProgress { get; set; }
}
