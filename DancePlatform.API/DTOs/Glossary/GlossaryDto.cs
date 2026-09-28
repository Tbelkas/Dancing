namespace DancePlatform.API.DTOs.Glossary;

/// <summary>A style's glossary on the index — just the size of it and the caller's progress.</summary>
public class GlossarySummaryDto
{
    public int StyleId { get; set; }
    public string StyleName { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;
    public int TermCount { get; set; }

    /// <summary>Terms that can be marked learned — moves, not concepts.</summary>
    public int MoveCount { get; set; }

    /// <summary>Of <see cref="MoveCount"/>, how many the caller has marked learned (0 when anonymous).</summary>
    public int LearnedCount { get; set; }
}

public class GlossaryDto : GlossarySummaryDto
{
    /// <summary>In authored order, each holding its terms in authored order.</summary>
    public List<GlossaryCategoryDto> Categories { get; set; } = new();
}

public class GlossaryCategoryDto
{
    public string Name { get; set; } = string.Empty;
    public List<GlossaryTermDto> Terms { get; set; } = new();
}

public class GlossaryTermDto
{
    public int Id { get; set; }
    public string Slug { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public List<string> Aliases { get; set; } = new();
    public string Summary { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public List<string> Steps { get; set; } = new();
    public List<string> Tips { get; set; } = new();

    /// <summary>Only slugs that exist in this glossary, so every one renders as a working link.</summary>
    public List<GlossaryRefDto> Related { get; set; } = new();

    public string Difficulty { get; set; } = "None";
    public bool IsLearnable { get; set; }
    public bool IsLearned { get; set; }

    /// <summary>The catalog move that demonstrates it; null when there's no video for it yet.</summary>
    public GlossaryDanceDto? Dance { get; set; }
}

public class GlossaryRefDto
{
    public string Slug { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
}

public class GlossaryDanceDto
{
    public int Id { get; set; }
    public string Slug { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;
    public int VideoCount { get; set; }
    public string? ThumbnailVideoId { get; set; }
    public string? ThumbnailPlatform { get; set; }
}

public class SetGlossaryLearnedRequest
{
    public bool Learned { get; set; }
}
