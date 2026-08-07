namespace DancePlatform.API.DTOs.User;

public class PublicProfileDto
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
    public string? AvatarUrl { get; set; }
    public List<DanceRef> LearnedDances { get; set; } = new();

    /// <summary>
    /// The skill trees this user has chosen to share. Only ever their public ones — this is the
    /// discovery surface for a shared tree, since they deliberately don't join the roadmap index.
    /// Empty for a user who has shared none, which is the default.
    /// </summary>
    public List<SharedRoadmapRef> SharedRoadmaps { get; set; } = new();
}

/// <summary>A shared tree as it appears on its owner's profile — enough to name it and link to it.</summary>
public record SharedRoadmapRef(string Slug, string Title, string Subtitle, string StyleName, int StepCount);
